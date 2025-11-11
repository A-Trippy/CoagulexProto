/*+++++++++++++++++++++++++++++----------=---=========================================================================================================/*************************************************** 
 CPCA Prototype Heater Control Software

 Inputs: 2x Adafruit MAX31865 Pt100 temperature sensor board 


 Arduino Micro Pinout

 MOSI MOSI for SPI devices
 SS
 TX   Unused, dedicated to USB serial comm
 RX   Unused, dedicated to USB serial comm
 RST  Unused  
 GND  GND
 D2   Rig1 CS, to header X1
 D3   Unused
 D4   Spare MOSFET gate
 D5   Indicator LED1
 D6   Indicator LED2
 D7   Indicator LED3
 D8   Indicator LED4
 D9   Indicator LED5
 D10  Indicator LED6
 D11  Rig1 Overtemp pin (input)
 D12  Buzzer Output
 D13  Unused
 3V3
 REF
 A0   Rig1 SW OK pin (output)
 A1   Rig1 Heater drive signal (output)
 A2   Rig2 SW OK pin (output)
 A3   Rig2 Heater drive signal (output)
 A4   Rig2 Overtemp pin (input)
 A5   Rig2 CS, to header X3
 MISO MISO for SPI devices
 SCK  CLK for SPI devices
 
 
 ****************************************************/

 /************
  * Header pairings:
  * Rig 1 
  * RTD: X1
  * 
  * Rig 2
  * RTD: X3
  * LED J6
  * HTR: J4
  */

#include <Adafruit_MAX31865.h>
#include <PID_v1.h>
#include <EEPROM.h>


// use hardware SPI, just pass in the CS pin
Adafruit_MAX31865 ch1 = Adafruit_MAX31865(2);
Adafruit_MAX31865 ch2 = Adafruit_MAX31865(A5);


const int led1 = 5; // Rig 1 Green LED 
const int led2 = 6; // Rig 1 Yellow LED
const int led3 = 7; // Rig 2 Green LED
const int led4 = 8; // Rig 2 Yellow LED
const int led5 = 9; // Rig 1 Red LED
const int led6 = 10; // Rig 2 Red LED
const int buzzer = 12;
const int rig1drive = 15;
const int rig2drive = 17;

const int RIG1OKTEMPLED = 5;
const int RIG1NOTOKTEMPLED = 6;
const int RIG2OKTEMPLED = 7;
const int RIG2NOTOKTEMPLED = 8;
const int OVERTEMPLED1 = 9;
const int OVERTEMPLED2 = 10;

int Temp1Offset = 0. ;
int Temp2Offset = 0. ;


// The value of the Rref resistor. Use 430.0 for PT100 and 4300.0 for PT1000
#define RREF      430.0
// The 'nominal' 0-degrees-C resistance of the sensor
// 100.0 for PT100, 1000.0 for PT1000
#define RNOMINAL  100.0


#define RSETPOINT 114.56 //pt100 resistance at 37.5 deg C in ohms

#define Pfactor 80 // Proportional factor
#define Ifactor 0 // Integral factor
#define Dfactor 15 // Derivative factor


double Setpoint1, Setpoint2, Rig1Input, Rig2Input, Rig1Output, Rig2Output;
PID PID1(&Rig1Input, &Rig1Output, &Setpoint1, Pfactor, Ifactor, Dfactor, DIRECT); //set up Rig1 PID with pointers
PID PID2(&Rig2Input, &Rig2Output, &Setpoint2, Pfactor, Ifactor, Dfactor, DIRECT); //set up Rig2 PID with pointers


void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("CPCA REV E");
    
  pinMode(2,OUTPUT);
  pinMode(4,OUTPUT);
  pinMode(5,OUTPUT);
  pinMode(6,OUTPUT);
  pinMode(7,OUTPUT);
  pinMode(8,OUTPUT);
  pinMode(9,OUTPUT);
  pinMode(10,OUTPUT);
  pinMode(11,INPUT);
  pinMode(12,OUTPUT);
  pinMode(13,INPUT);
  pinMode(A0,OUTPUT);
  pinMode(A1,OUTPUT);
  pinMode(A2,OUTPUT);
  pinMode(A3,OUTPUT);
  pinMode(A4,INPUT);
  pinMode(A5,OUTPUT);

  digitalWrite(A5,HIGH);
  digitalWrite(2,HIGH);
  digitalWrite(A1,LOW);
  digitalWrite(A0,HIGH);
  digitalWrite(A2,HIGH);
  
  POST();

  ch1.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary
  ch2.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary

  //uint16_t LowT1 = ch1.readLThresh();
  //uint16_t LowT2 = ch2.readLThresh();

  //Serial.print("Channel 1 Low Threshold ");
  //Serial.println(LowT1);
  //Serial.print("Channel 2 Low Threshold ");
 // Serial.println(LowT2);
  
  PID1.SetOutputLimits(0,100); //Limit PWM to reduce load on power supply
  PID2.SetOutputLimits(0,100);

  PID1.SetSampleTime(400);
  PID2.SetSampleTime(400);

  Rig1Input = (double)ch1.readRTD();
  Rig1Input /= 32768;
  Rig1Input *= RREF;
  
  Rig2Input = (double)ch2.readRTD();
  Rig2Input /= 32768;
  Rig2Input *= RREF;

  Temp1Offset = int((EEPROM.read(0) << 8) + EEPROM.read(1)); //EEPROM bytes 0 and 1 correspond to signed integer, that gets multiplied by .01 to set calibration offset of setpoint
  Temp2Offset = ((int((EEPROM.read(2) << 8) + EEPROM.read(3))));
  
  Setpoint1 = RSETPOINT + ((int((EEPROM.read(4) << 8) + EEPROM.read(5)))*.01);  //Similarly, bytes 4-6 used to store info on setpoint adjustment
  Setpoint2 = RSETPOINT + ((int((EEPROM.read(6) << 8) + EEPROM.read(7)))*.01);

  PID1.SetMode(AUTOMATIC); //turn on rig1 PID
  PID2.SetMode(AUTOMATIC); //turn on rig2 PID
  
  Serial.print("Kp = "); Serial.println(PID1.GetKp());
  Serial.print("Ki = "); Serial.println(PID1.GetKi());  
  Serial.print("Kd = "); Serial.println(PID1.GetKd()); 
  Serial.print("Mode = "); Serial.println(PID1.GetMode()); 
  Serial.print("Rig 1 Temp Offset = "); Serial.print(Temp1Offset); Serial.print("\t"); Serial.print("Rig 2 Temp Offset = "); Serial.print(Temp2Offset);
  Serial.print("Rig 1 Setpoint Offset = "); Serial.print(Setpoint1 - RSETPOINT); Serial.print("\t"); Serial.print("Rig 2 Setpoint Offset = "); Serial.println(Setpoint2 - RSETPOINT);
  Serial.println("************************************************************************************************************");
  Serial.println("************************************************************************************************************");
  Serial.println("************************************************************************************************************");

  

 

}
void loop() {
  float Rig1Temp;
  float Rig2Temp;
  Rig1Input = ch1.readRTD();
  Rig1Input /= 32768;
  Rig1Input *= RREF;
  Serial.print("Rig 1 Resistance = "); Serial.print(Rig1Input,8); Serial.print("\t");
  Rig1Temp = (ch1.temperature(100,RREF) + (.01 * Temp1Offset)); 
  PID1.Compute();
  
 
  digitalWrite(A1,HIGH);
  delay(Rig1Output);
  digitalWrite(A1,LOW);
  delay(200-Rig1Output);
  digitalWrite(A1,HIGH);
  delay(Rig1Output);
  digitalWrite(A1,LOW);
  
 
  
  Rig2Input = ch2.readRTD();
  Rig2Input /= 32768;
  Rig2Input *= RREF;
  Serial.print("Rig 2 Resistance = "); Serial.print(Rig2Input,8); Serial.print("\t"); Serial.print("\t");
  Rig2Temp = (ch2.temperature(100,RREF) + float(.01 * Temp2Offset));
  PID2.Compute();
 
  
  
  digitalWrite(A3,HIGH);
  delay(Rig2Output);
  digitalWrite(A3,LOW);
  delay(200-Rig2Output);
  digitalWrite(A3,HIGH);
  delay(Rig2Output);
  digitalWrite(A3,LOW);
  Serial.print("T1:"); Serial.print(Rig1Temp); Serial.print(" "); Serial.print("T2:"); Serial.print(Rig2Temp); Serial.print("\t");
  Serial.print(Rig1Output,4); Serial.print(" ");Serial.println(Rig2Output,4);
  delay(500);
  checktempfaults();
  calshift();
  checkitco();

  if(Rig1Temp <36.5){
    digitalWrite(RIG1NOTOKTEMPLED,HIGH);
    digitalWrite(RIG1OKTEMPLED,LOW);  
  }
  else if(Rig1Temp >36.5 && Rig1Temp < 38.5){
    digitalWrite(RIG1OKTEMPLED,HIGH);
    digitalWrite(RIG1NOTOKTEMPLED,LOW);
  }
  

  if(Rig2Temp <36.5){
    digitalWrite(RIG2NOTOKTEMPLED,HIGH);
    digitalWrite(RIG2OKTEMPLED,LOW);
  }
  else if(Rig2Temp > 36.5 && Rig2Temp < 38.5){
    digitalWrite(RIG2OKTEMPLED,HIGH);
    digitalWrite(RIG2NOTOKTEMPLED,LOW);
  }
}


void checkitco(void){
  if (!digitalRead(11) | !digitalRead(A4)){ //if either independent temp sensor is triggered...shut down everthing
    digitalWrite(buzzer,HIGH); //Drive buzzer;
    delay(500);
    digitalWrite(buzzer,LOW); //Drive buzzer;
    delay(500);
    digitalWrite(buzzer,HIGH); //Drive buzzer;
    delay(500);
    digitalWrite(buzzer,LOW); //Drive buzzer;
    delay(500);
    digitalWrite(buzzer,HIGH); //Drive buzzer;
    delay(500);
    digitalWrite(buzzer,LOW); //Drive buzzer;
    delay(500);
    digitalWrite(OVERTEMPLED1,HIGH); //Turn on overtemp leds 
    digitalWrite(OVERTEMPLED2,HIGH);
    digitalWrite(RIG1NOTOKTEMPLED,LOW); //Turn off low temp and normal temp led
    digitalWrite(RIG2NOTOKTEMPLED,LOW);
    digitalWrite(RIG1OKTEMPLED,LOW);
    digitalWrite(RIG2OKTEMPLED,LOW);
    digitalWrite(A0,LOW); //drive Rig1SWOK low
    digitalWrite(rig1drive,LOW);
    digitalWrite(A2,LOW); //drive Rig2SWOK low
    digitalWrite(rig2drive,LOW);
    Serial.println("OVERTEMP DETECTED");
    while(1){}; //requires reset to turn off
  }
}

void checktempfaults(void){
  uint8_t fault = ch1.readFault();
  if (fault) {
    Serial.println("Rig 1 Fault");
    Serial.print("Fault 0x"); Serial.println(fault, HEX);
    if (fault & MAX31865_FAULT_HIGHTHRESH) {
      Serial.println("RTD High Threshold"); 
    }
    if (fault & MAX31865_FAULT_LOWTHRESH) {
      Serial.println("RTD Low Threshold"); 
    }
    if (fault & MAX31865_FAULT_REFINLOW) {
      Serial.println("REFIN- > 0.85 x Bias"); 
    }
    if (fault & MAX31865_FAULT_REFINHIGH) {
      Serial.println("REFIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault & MAX31865_FAULT_RTDINLOW) {
      Serial.println("RTDIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault & MAX31865_FAULT_OVUV) {
      Serial.println("Under/Over voltage"); 
    }
    ch1.clearFault();
  }
  fault = ch2.readFault();
  if (fault) {
    Serial.println("Rig 2 Fault");
    Serial.print("Fault 0x"); Serial.println(fault, HEX);
    if (fault & MAX31865_FAULT_HIGHTHRESH) {
      Serial.println("RTD High Threshold"); 
    }
    if (fault & MAX31865_FAULT_LOWTHRESH) {
      Serial.println("RTD Low Threshold"); 
    }
    if (fault & MAX31865_FAULT_REFINLOW) {
      Serial.println("REFIN- > 0.85 x Bias"); 
    }
    if (fault & MAX31865_FAULT_REFINHIGH) {
      Serial.println("REFIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault & MAX31865_FAULT_RTDINLOW) {
      Serial.println("RTDIN- < 0.85 x Bias - FORCE- open"); 
    }
    if (fault & MAX31865_FAULT_OVUV) {
      Serial.println("Under/Over voltage"); 
    }
    ch2.clearFault();
  }
}
void calshift(void){
  //Adjust Calibration for temp sensor. use, '+' and '-' for rig 1 temp measurement fine offset adjustment '.' and ',' for rig 2 temp measurement fine offset adjustment. use '8' and '9' and 'b' and 'n' for coarse adjustment on rigs 1 and 2 respectively. 
  //'[' and ']' for rig 1 setpoint adjustment, ';' and ''' for rig 2 setpoint adjustment
  if (Serial.available() > 0){
    // get incoming byte
    char inChar = Serial.read();
    int calval;
    switch(inChar){
      case '+':
      calval = int((EEPROM.read(0) << 8) + EEPROM.read(1));
      calval += 1;
      EEPROM.write(0,calval >> 8); //MSB
      EEPROM.write(1,calval);
      Temp1Offset = calval;
      break;
      case '-':
      calval = int((EEPROM.read(0) << 8) + EEPROM.read(1));
      calval -= 1;
      EEPROM.write(0,calval >> 8);
      EEPROM.write(1,calval);
      Temp1Offset = calval; 
      break;
      case '.':
      calval = int((EEPROM.read(2) << 8) + EEPROM.read(3));
      calval += 1;
      EEPROM.write(2,calval >> 8);
      EEPROM.write(3,calval);
      Temp2Offset = calval; 
      break;
      case ',':
      calval = int((EEPROM.read(2) << 8) + EEPROM.read(3));
      calval -= 1;
      EEPROM.write(2,calval >> 8);
      EEPROM.write(3,calval); 
      Temp2Offset = calval;
      break;
       case '9':
      calval = int((EEPROM.read(0) << 8) + EEPROM.read(1));
      calval += 10;
      EEPROM.write(0,calval >> 8);
      EEPROM.write(1,calval);
      Temp1Offset = calval;
      break;
      case '8':
      calval = int((EEPROM.read(0) << 8) + EEPROM.read(1));
      calval -= 10;
      EEPROM.write(0,calval >> 8);
      EEPROM.write(1,calval);
      Temp1Offset = calval; 
      break;
      case 'n':
      calval = int((EEPROM.read(2) << 8) + EEPROM.read(3));
      calval += 10;
      EEPROM.write(2,calval >> 8);
      EEPROM.write(3,calval);
      Temp2Offset = calval; 
      break;
      case 'b':
      calval = int((EEPROM.read(2) << 8) + EEPROM.read(3));
      calval -= 10;
      EEPROM.write(2,calval >> 8);
      EEPROM.write(3,calval); 
      Temp2Offset = calval;
      break;
      case ']':
      calval = int((EEPROM.read(4) << 8) + EEPROM.read(5));
      calval += 1;
      EEPROM.write(4,calval >> 8);
      EEPROM.write(5,calval);
      Setpoint1 = RSETPOINT + ((int((EEPROM.read(4) << 8) + EEPROM.read(5)))*.01);
      break;
      case '[':
      calval = int((EEPROM.read(4) << 8) + EEPROM.read(5));
      calval -= 1;
      EEPROM.write(4,calval >> 8);
      EEPROM.write(5,calval);
      Setpoint1 = RSETPOINT + ((int((EEPROM.read(4) << 8) + EEPROM.read(5)))*.01);
      break;
      case '\'':
      calval = int((EEPROM.read(6) << 8) + EEPROM.read(7));
      calval += 1;
      EEPROM.write(6,calval >> 8);
      EEPROM.write(7,calval);
      Setpoint2 = RSETPOINT + (calval * .01);
      break;
      case ';':
      calval = int((EEPROM.read(6) << 8) + EEPROM.read(7));
      calval -= 1;
      EEPROM.write(6,calval >> 8);
      EEPROM.write(7,calval); 
      Setpoint2 = RSETPOINT + (calval *.01);
      break;
      default:
      Serial.println("Invalid Entry");
      break;
    }
    Serial.print("Temp1Offset: "); Serial.print(Temp1Offset); Serial.print("; Temp2Offset: "); Serial.print(Temp2Offset); Serial.print("; Setpoint1: "); Serial.print(Setpoint1); Serial.print("; Setpoint2:"); Serial.println(Setpoint2);
     
  }
}

void POST(void){
  Serial.print("POST TEST....");
  digitalWrite(A0,LOW); 
  digitalWrite(A1,LOW);
  digitalWrite(A2,LOW);
  digitalWrite(A3,LOW);
  digitalWrite(buzzer,HIGH); //Test Buzzer
  delay(1000);
  digitalWrite(buzzer,LOW);
  for (int i= led1 ; i<=led6; i++) //Turn on each LED one at a time
  {
    digitalWrite(i,HIGH); 
    delay(1000);
    digitalWrite(i,LOW);
  }
  for (int i= led1 ; i<=led6; i++) //Turn off LEDs
  {
    digitalWrite(i,LOW); 
  }
  digitalWrite(A0,HIGH);//Rig1 Heater Check
  digitalWrite(A1,HIGH);
  delay(1000);
  digitalWrite(A0,LOW);
  digitalWrite(A1,LOW);
  digitalWrite(A2,HIGH); //Rig2 Heater Check
  digitalWrite(A3,HIGH);
  delay(1000);
  digitalWrite(A2,LOW);
  digitalWrite(A3,LOW);
  Serial.println("Complete");
  digitalWrite(A0,HIGH);//set SWOK? pins to high in preparation for normal operation
  digitalWrite(A2,HIGH);
}

/*
void drivehtr(int chan, int error, int duration){
  if (chan == 1){
    if (error > 0){
      analogWrite(10,map(error, 0, 50, 0, 128);
      delay(duration);
      analogWrite(10,0);         
     }
  }

  if (chan ==2){
    if (error > 0){
      analogWrite(9, map(error, 0, 50, 0, 128);
      delay(duration);
      analogWrite(9,0);
    }
  }
}
*/
