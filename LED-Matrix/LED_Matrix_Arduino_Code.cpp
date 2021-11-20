#include <Arduino.h>
#include <MD_Parola.h>

typedef enum receive_status {
  STANDBY, READING_DATA, READING_START, READING_END
  } Receive_Status;

const int NUM_LEDS = 64;
byte led_vals[NUM_LEDS];
boolean new_data = false;

void receive_data();
void update_led_matrix();

void setup() {
  // initialize all the LED Matrix stuff

  for (int i = 0; i < NUM_LEDS; i++) {
    led_vals[i] = 0;
  }
  Serial.begin(115200);
}

void loop() {
  receive_data();
  update_led_matrix();
}

void receive_data() {
  byte val;
  static Receive_Status recv_stat = STANDBY;
  static unsigned int marker_index, led_index;

  String start_marker = "<data>";
  String end_marker = "</data>";

  while(Serial.available() > 0 && !new_data) {
    // get data from the serial port
    val = Serial.read();

    switch(recv_stat) {
    case READING_START:
      // reached end of start_marker... enter READING_DATA state
      if (marker_index >= start_marker.length()) {
        recv_stat = READING_DATA;
        led_vals[0] = val;
        led_index = 1;
      }
      // val matches the next character in start_marker
      else if (val == start_marker[marker_index]) {
        marker_index++;
      }
      // val does not match the next expected character in start_marker
      // this is not a valid start marker, so reset to STANDBY
      else {
        recv_stat = STANDBY;
      }
      break;
      
    case READING_END:
      // reached the end of end_marker... return to STANDBY state & reset variables
      if (marker_index >= end_marker.length() - 1) {
        recv_stat = STANDBY;
        led_index = 0;
        new_data = true;
      }
      // val matches the next character in end_marker
      else if (val == end_marker[marker_index]) {
          marker_index++;
      }
      // val does not match the next expected character in end_marker...
      // this is not a valid end marker, so backtrack and add data into led_vals
      // and reset to READING_DATA state
      else {
        for(unsigned int i = 0; i < marker_index; i++) {
          led_vals[led_index++] = end_marker[i];
        }
        led_vals[led_index++] = val;
        recv_stat = READING_DATA;
      }
      break;

    case READING_DATA:
      // first character in end_marker is encountered
      // try reading the full end_marker to check
      if (val == end_marker[0]) {
        marker_index = 1;
        recv_stat = READING_END;
      }

      // otherwise... continue adding to led_vals
      else {
        led_vals[led_index++] = val;
        // overflow protection:
        if (led_index >= NUM_LEDS) {
          led_index = NUM_LEDS - 1;
        }
      }
      break;

    default: // STANDBY
      if (val == start_marker[0]) {
        marker_index = 1;
        recv_stat = READING_START;
      }
    }
  }
}
