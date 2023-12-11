#include <Servo.h>
#include <math.h>

int width = 640, height = 480; // total resolution of the video
float xpos = 85, ypos = 140; // initial positions of both Servos
// define the centers for the object and the hight
int x_mid, y_mid, objheight;
double dist,dx,dy;
Servo x, y; //define the servo motors

void setup() {
 Serial.begin(115200); //Serial bandwidth
 x.attach(5); //control pin for pan
 y.attach(6); //control pin rot tilt
 x.write(xpos); //send initial pan position
 y.write(ypos); //send initial tilt position

}


//read the sent data from jetson (x and y for the centers and h for the hight)
 while(Serial.available()){Serial.read();}
 if (Serial.available() > 0)
 {
 if (Serial.read() == 'X')
 {
 x_mid = Serial.parseInt();
 if (Serial.read() == 'Y')
 {
 y_mid = Serial.parseInt();
 if (Serial.read() == 'H')
 objheight = Serial.parseInt();
 }
 }
 else
 return;

dx=width/2 - x_mid;
dy=height/2 - y_mid;
dist=-1.4419*double(objheight)+834.42;

if ((x_mid > ((width / 2) + 30)) || (x_mid < ((width / 2) - 30))) // this is the range where the center(x) of the body can be in
{
xpos=xpos+4*(dx/450)*(350/abs(dist)); //every loop this equation is done tell the center(x) in range
x.write(xpos);
}
if ((y_mid > height / 2 + 30) || (y_mid < height / 2 - 30)) // this is the range where the center(y) of the body can be in
{
ypos=ypos-3*(dy/225)*(350/abs(dist)); //every loop this equation is done tell the center(y) in range
y.write(ypos);
}

 // if the servo degree is outside its range
 if (xpos >= 160)
 xpos = 160;
 else if (xpos <= 10)
 xpos = 10;
 if (ypos >= 170)
 ypos = 170;
 else if (ypos <= 80)
 ypos = 80;
