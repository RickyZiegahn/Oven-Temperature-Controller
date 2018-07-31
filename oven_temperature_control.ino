/*
 * Version 1.4 last updated 31-July-2018
 * https://github.com/RickyZiegahn/X-Ray_Diffraction
 * Made for McGill University under D.H. Ryan
 */

#include <SPI.h>
#include <Adafruit_MAX31855.h>
#define channelamount 2
int CLK = 2; //clock pin
int DO = 3; //data out pin
int sample_pin = 4;
int CS[channelamount] = {5,6}; //array of chip select pins
int relay[channelamount] = {7,8}; //array of relay pin list

int channels[channelamount];
double set_temperature[channelamount];
double measured_temperature[channelamount];
double sample_temperature = 0;
double error[channelamount];
double band[channelamount];
double proportional_term[channelamount];
double integral_term[channelamount];
double integral_time[channelamount]; //integral times in milliseconds
double output[channelamount];
int up_time[channelamount]; //time (ms) that the oven is on for
int time_1;
int time_2;
int dt = 1000; //time in milliseconds
int flag[channelamount]; //flag for the oven to be enabled or disabled, include a 0 for each channel

//initialize the thermocouples
Adafruit_MAX31855 thermocouple_sample(CLK, sample_pin, DO);
Adafruit_MAX31855 thermocouple_0(CLK, CS[0], DO);
Adafruit_MAX31855 thermocouple_1(CLK, CS[1], DO);
void read_temperature(int channel) {
  /*
   * Reads the temperature of a given channel.
   */
  if (channel == 0) {
    measured_temperature[channel] = thermocouple_0.readCelsius(); //no way to store the thermocouple objects in an array
  }
  if (channel == 1) {
    measured_temperature[channel] = thermocouple_1.readCelsius();
  }
  if (isnan(measured_temperature[channel])) {
    flag[channel] = 1;
    output[channel] = 0;
    proportional_term[channel] = 0;
    integral_term[channel] = 0;
    up_time[channel] = 0;
    digitalWrite(relay[channel],LOW);
  }
  Serial.println(measured_temperature[channel]);
}

void wait_for_input() {
  /*
   * Stops the arduino from proceeding without receiving all its parameters. Without this, 
   * the arduino might not update some parameters and the python code will think it did.
   */
  while(!Serial.available()) {
  }
}

void accept_parameters(int channel) {
  /*
   * Accepts the set temperature, band, and integral time for a given channel.
   */
  wait_for_input();
  set_temperature[channel] = Serial.parseInt() / 4;
  Serial.read();
  band[channel] = Serial.parseInt() / 4;
  Serial.read();
  integral_time[channel] = Serial.parseInt() / 4;
  Serial.read();
}

void calculate_error(int channel) {
  /*
   * Calculates the error for a given channel.
   */
  for (int i = 0; i < (measurementamount - 1); i++) {
    error[channel] = error[channel];
  }
  error[channel] = set_temperature[channel] - measured_temperature[channel];
}

void calculate_proportional_term(int channel) {
  /*
   * Calculates the proportional term for a given channel.
   */
  proportional_term[channel] = error[channel] / band[channel];
}

void calculate_integral_term(int channel) {
  /*
   * Calculates the integral term using the formula seen above, for a given channel.
   */
  if (-1 * band[channel]/2 < error[channel] and error[channel] < band[channel]/2) {
    integral_term[channel] += (error[channel] * dt) / (band[channel] * integral_time[channel]);
  }
}

void calculate_output(int channel) {
  /*
   * Calculates the output (a value between 0 and 1, representing the fraction of full power needed)
   * using the formula seen above, for a given channel. The function makes sure that the output is at 
   * least 0 and at most 1. The function also doesn’t let a wild integral term keep it permanently on 
   * or off, if the temperature exits the band, it will be fully on if below and fully off if above.
   */
  output[channel] = proportional_term[channel] + integral_term[channel] + 0.5;
  //output cannot be more than one
  if (output[channel] > 1) {
    output[channel] = 1;
    }
  if (output[channel] < 0) {
    output[channel] = 0;
  }
  //if it is out of the band, it should be zero or 1 no matter what. this next bit is to prevent
  //the integral term from permanently keeping it on full power
  if (-1 * band[channel]/2 > error[channel]) {
    output[channel] = 0;
  }
  if (error[channel] > band[channel]/2) {
    output[channel] = 1;
  }
}

void calculate_up_time(int channel) {
  /*
   * Calculates the fraction of time (dt = 1 second), by multiplying the time between measurements 
   * by the output, for a given channel.
   */
  up_time[channel] = round(output[channel] * dt);
}

void give_weights(int channel) {
  /*
   * Writes the value of the proportional term, integral term, and output to the serial, used for 
   * logging purposes.
   */
  Serial.println(output[channel]);
  Serial.println(proportional_term[channel]);
  Serial.println(integral_term[channel]);
}

void check_time(int channel) {
  /*
   * For a given channel, check if the time the heater has been on has not exceeded the time it is
   * supposed to be on. If it has, turn it off, if it has not, keep it on.
   */
  if (time_2 - time_1 < up_time[channel]) {
    digitalWrite(relay[channel], HIGH);
  }
  else {
    digitalWrite(relay[channel], LOW);
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  pinMode(relay[0], OUTPUT);
}

void loop() {
  for (int channel = 0; channel < channelamount; channel++) {
    //ensure that the oven wasn't on so that if it hangs, it will not stay on
    digitalWrite(relay[channel], LOW);
  }
  for (int channel = 0; channel < channelamount; channel++) {
    accept_parameters(channel);
    //reset integral term in case the temperature was changed before it settled
    integral_term[channel] = 0;
  }
  while(!Serial.available()) {
    for (int channel = 0; channel < channelamount; channel++) {
      read_temperature(channel);
      if (flag[channel] == 0) {
        calculate_error(channel);
        calculate_proportional_term(channel);
        calculate_integral_term(channel);
        calculate_output(channel);
        calculate_up_time(channel);
      }
      give_weights(channel);
    }
    sample_temperature = thermocouple_sample.readCelsius();
    Serial.println(sample_temperature);
    //set time_1 and time_2 to the same value so dt = 0
    time_1 = millis();
    time_2 = millis();
    while(time_2 - time_1 < dt) {
      for (int channel = 0; channel < channelamount; channel++) {
        if (flag[channel] == 0) {
          check_time(channel);
        }
        if (flag[channel] == 1) {
          digitalWrite(relay[channel], LOW);
        }
      }
      time_2 = millis();
    }
  }
}
