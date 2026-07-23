uniform float uTime;
uniform float uLayer;

varying vec3 vNormal;
varying vec3 vPosition;
varying vec3 vWorldPosition;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 345.45));
	p += dot(p, p + 34.23);
	return fract(p.x * p.y);
}

void main(){

vec3 gold = vec3(0.95,0.72,0.28);
vec3 amber = vec3(0.98,0.56,0.14);
vec3 hot = vec3(1.0,0.9,0.64);

float r = length(vPosition);
float sphericalBand = 0.5 + 0.5 * sin(vPosition.y * 14.0 + uTime * 2.8);
float longitude = atan(vPosition.z, vPosition.x);
float lat = atan(vPosition.y, length(vPosition.xz));

vec2 cell = vec2(
	floor((longitude + 3.14159265) * 7.8),
	floor((lat + 1.5707963) * 13.2)
);
float keep = step(0.44, hash21(cell + floor(uTime * 0.8)));

float meridian = smoothstep(0.97, 1.0, abs(sin(longitude * 26.0 + uTime * 1.2)));
float parallel = smoothstep(0.97, 1.0, abs(sin(lat * 46.0 - uTime * 0.9)));
float grid = max(meridian, parallel) * keep;

float scan = smoothstep(0.8, 1.0, sin(vPosition.y * 7.0 - uTime * 2.0) * 0.5 + 0.5);
float radialPulse = smoothstep(0.95, 1.0, sin((r * 31.0) - uTime * 4.4) * 0.5 + 0.5);
float circuitry = max(grid, radialPulse * 0.34 + scan * 0.2);

vec3 viewDir = normalize(cameraPosition - vWorldPosition);
float fresnel = pow(1.0 - max(dot(normalize(vNormal), viewDir), 0.0), 2.7);

vec3 base = mix(gold, amber, sphericalBand) * 0.16;
vec3 color = base;
color += hot * circuitry * (0.4 + 0.2 * uLayer);
color += amber * fresnel * (0.36 + 0.34 * uLayer);

float shellOuter = 1.0 - smoothstep(1.02, 1.16, r);
float shellInner = smoothstep(0.9, 0.99, r);
float shell = shellInner * shellOuter;
float alpha = (0.014 + 0.24 * circuitry + fresnel * 0.2) * shell;
alpha *= mix(0.8, 1.18, uLayer);

gl_FragColor = vec4(color, alpha);

}