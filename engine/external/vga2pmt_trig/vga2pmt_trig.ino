#define NSAMPLES 4
#define PULSE_WIDTH_120HZ (1000000/(120*6/2))
#define PULSE_WIDTH_60HZ (1000000/(60*6/2))
#define _60HZ_US (1000000/60)*2
#define _120HZ_US (1000000/120)*2
byte input_state;
unsigned long period=0;
unsigned long pulse_width=0;
unsigned long pulse_delay=200;
unsigned long post_pulse_delay=2000;
unsigned long period_calc;
unsigned long periods[NSAMPLES];
byte index=0;
bool frq_decided;
unsigned long last_isr,now;

ISR(INT0_vect) {
  cli();
  input_state++;
  if (input_state==2)
  {
    input_state=0;
  }
  if ((input_state==1)||1)
  {    
    //TODO: check level before turning on stim led to avoid pmt gets saturated
    //TODO: serial port msg about number of improperly fired interrupts
    now=micros();
    if (1)
    {
      delayMicroseconds(pulse_delay);
      PORTD|=1<<6;//pmt off
      PORTD|=1<<7;//stim led on
      delayMicroseconds(pulse_width);
      PORTD&=~(1<<7);//stim led off
      PORTD&=~(1<<6);//pmt on 
      while(((PIND&(1<<2))!=0))
      {
      }
      //delayMicroseconds(post_pulse_delay);
    } 
    else
    {
      //overflow, do not update period
    }    
  }
  sei();
}


void setup() {
  Serial.begin(115200);
  DDRD&=~(1<<2);//pind2 int0
  DDRD|=(1<<7);//pind7 stimulus led
  DDRD|=(1<<6);//pind6 pmt enable
  PORTD&=~(1<<7);
  PORTD&=~(1<<6);
  EICRA|=3;//both edges
  EIMSK|=1;
  input_state=0;
  last_isr=micros();
  period=PULSE_WIDTH_120HZ;
  frq_decided=false;
  frq_decided=true;
  pulse_width=200;//500 us
  sei();

}

void loop() {
  /*digitalWrite(7, HIGH);
  delay(2);
  digitalWrite(7, LOW);
  delay(3);*/

}
