/*
Arduino pin 0-1: reserved
Arduino pin 2-4: input: level changes are captured and timestamps are sent over usb/serial port
Arduino pin 5-7: output: level, pulse or pulse train waveform can be generated.

Commands:
'o': set level, + 1byte binary packed pin values 
'p': generate single pulse on pins determined by subsequent byte value. The lenght of the pulse is 2 ms (PULSE_WIDTH)
'f': set frequency, subsequent byte is interpreted in Hz
'w': toggle enable waveform state
'e': enable send input pin state
'd': disable send input pin state
*/
#define COMPARE 116//2 kHz, FCPU is 14.7456MHz, comp=FCPU/(f*prescale)+1
#define PRESCALE 4 //64 prescale
#define IDLE_ST 0
#define WAIT_PAR_ST 1
#define OUTPORT_MASK 0xe0
#define INPORT_MASK 0x1C
#define PULSE_WIDTH 2

char b;
byte state;
byte par;

byte cmd = 0;
byte send_data=true;
byte port,port_prev,waveform_pin;
unsigned long time;
bool force_read_pin=false;
bool enable_waveform=false;
byte frequency;
int period;

ISR(TIMER1_COMPA_vect) {
   PORTB |=(1<<2);//D10 output
   TCNT1L=0;
   TCNT1H=0;
   time = millis();
   port=PIND&INPORT_MASK;
   if ((port!=port_prev) || force_read_pin)
   {
     if (send_data)
     {
       Serial.print(time);
       Serial.print(" ms: ");
       Serial.print(port,HEX);
       Serial.print("\r\n");
     }
     force_read_pin=false;
     port_prev=port;
   }
   PORTB &=~(1<<2);
}

void init_digital_input_timer()
{
   TCCR1B = PRESCALE;
   OCR1AH = 0;
   OCR1AL = COMPARE;
   TIMSK1 |= 1<<1;
}

void setup() {
  Serial.begin(115200);
  DDRB|=1<<2;//D10 output for debugging
  DDRD=OUTPORT_MASK;//port 2-4 input, port 5-7 output
  PORTD=0x00;
  state=IDLE_ST;
  init_digital_input_timer();
  port_prev=0;
  port=0;
  frequency=0;
  pinMode(LED_BUILTIN, OUTPUT);
  sei();
}


void loop() {
  b = Serial.read();
  if (b!=-1) {
    switch (state)
    {
      case IDLE_ST:
        switch (b)
        {
          case 'o'://output
          case 'p'://pulse
            cmd=b;
            state=WAIT_PAR_ST;
            break;
          case 'r'://read pins
            force_read_pin=true;
            state=IDLE_ST;
            break;
          case 'e'://enable send data
            send_data=true;
            state=IDLE_ST;
            break;
          case 'd'://disable send data
            send_data=false;
            state=IDLE_ST;
            break;
          case 'f'://set frequency
            state=WAIT_PAR_ST;
            cmd=b;
          case 'w': //enable pulse train waveform
            cmd=b;
            state=WAIT_PAR_ST;
            break;
          default:
            state=IDLE_ST;
            break;
        }
        break;
      case WAIT_PAR_ST:
        par = b;
        switch (cmd) {
          case 'o':
              PORTD = par&OUTPORT_MASK;
              break;
          case 'p':
              PORTD |= par&OUTPORT_MASK;
              delay(PULSE_WIDTH);
              PORTD &= ~(par&OUTPORT_MASK);
              break;
          case 'f':
              frequency=par;
              period=1000/par/2;
              break;
          case 'w':
              waveform_pin=par;
              if (enable_waveform)
              {
                enable_waveform=false;
              }
              else
              {
                enable_waveform=true;
              }
              
              //enable_waveform=~enable_waveform;
              break;
          case 'a':
              break;
        }
        state=IDLE_ST;
        break;
      default:
        break;
    }  
  }
  if (enable_waveform)
  {
    PORTD |= waveform_pin&OUTPORT_MASK;
    digitalWrite(LED_BUILTIN, HIGH);
    delay(period);
    PORTD &= ~(waveform_pin&OUTPORT_MASK);
    digitalWrite(LED_BUILTIN, LOW);
    delay(period);
  }
  /*PORTD |= (1<<5)&OUTPORT_MASK;
  delay(50);
  PORTD &= ~((1<<5)&OUTPORT_MASK);
  delay(50);*/
}
