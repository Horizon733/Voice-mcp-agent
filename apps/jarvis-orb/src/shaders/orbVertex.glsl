uniform float uTime;
uniform float uLayer;

varying vec3 vNormal;
varying vec3 vPosition;
varying vec3 vWorldPosition;

void main(){

vNormal = normalize(normalMatrix * normal);

float wave =
sin(position.x*9.0+uTime*1.4)*0.006 +
sin(position.y*8.0-uTime*1.0)*0.006 +
sin(position.z*10.0+uTime*0.9)*0.006;

wave *= uLayer;

vec3 displaced =
position +
normal * wave;

vPosition = displaced;

vec4 worldPos = modelMatrix * vec4(displaced,1.0);
vWorldPosition = worldPos.xyz;

gl_Position =
projectionMatrix *
viewMatrix *
worldPos;

}