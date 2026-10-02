import React from 'react';
import { useCurrentFrame } from 'remotion';
import { Backdrop, W, H, frameDrift, RoughFilter } from './kit';

type PlanetSpec = {
	sky: string;
	skyTop?: string;
	bodyDark: string;
	bodyMid: string;
	bodyLight: string;
	rim: string;
	rimWidth?: number;
	seed?: number;
	horizon?: number; // 0..1 — where the limb crest sits
	fluid?: 'marble' | 'crater' | 'paint';
};

/**
 * PlanetTexture — the reference film's recurring composition: a huge curved
 * body occupying the lower frame, top rim catching light, dark sky above.
 * One parameterised implementation covers amber / teal / red / ink variants.
 */
export const Planet: React.FC<{ spec: PlanetSpec }> = ({ spec }) => {
	const {
		sky,
		skyTop,
		bodyDark,
		bodyMid,
		bodyLight,
		rim,
		rimWidth = 20,
		seed = 11,
		horizon = 0.52,
		fluid = 'crater',
	} = spec;
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 14, 300);

	const bodyCx = W * 0.5 + drift;
	const bodyR = W * 0.62;
	const bodyCy = H * horizon + bodyR; // limb crest sits exactly at the horizon line
	const crestY = bodyCy - bodyR;

	const freq = fluid === 'marble' ? '0.006 0.01' : fluid === 'paint' ? '0.01 0.016' : '0.014 0.02';

	return (
		<Backdrop>
			<defs>
				<linearGradient id="p-sky" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor={skyTop ?? sky} />
					<stop offset="1" stopColor={sky} />
				</linearGradient>
				<radialGradient id="p-body" cx="0.5" cy="0.06" r="1.15">
					<stop offset="0" stopColor={bodyLight} />
					<stop offset="0.22" stopColor={bodyMid} />
					<stop offset="0.62" stopColor={bodyDark} />
					<stop offset="1" stopColor="#050403" />
				</radialGradient>
				<RoughFilter id={`p-rough-${seed}`} scale={30} seed={seed} freq={freq} octaves={4} />
				<filter id={`p-surface-${seed}`} x="-5%" y="-5%" width="110%" height="110%">
					<feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={5} seed={seed + 5} />
					<feColorMatrix
						type="matrix"
						values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  1.1 1.1 1.1 0 -0.75"
					/>
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id={`p-rimglow-${seed}`} x="-40%" y="-40%" width="180%" height="180%">
					<feGaussianBlur stdDeviation={rimWidth * 0.9} />
				</filter>
			</defs>

			<rect width={W} height={H} fill="url(#p-sky)" />

			{/* atmosphere hugging the limb */}
			<circle
				cx={bodyCx}
				cy={bodyCy}
				r={bodyR + rimWidth * 2.2}
				fill="none"
				stroke={rim}
				strokeWidth={rimWidth * 3}
				opacity={0.5}
				filter={`url(#p-rimglow-${seed})`}
			/>

			{/* the body, rough-edges; the radial gradient alone carries the
				    limb light — no overlay stripe at this scale */}
			<g filter={`url(#p-rough-${seed})`}>
				<circle cx={bodyCx} cy={bodyCy} r={bodyR} fill="url(#p-body)" />
			</g>
			{/* internal surface texture clipped to the body */}
			<g filter={`url(#p-surface-${seed})`} opacity={fluid === 'marble' ? 0.5 : 0.34}>
				<circle cx={bodyCx} cy={bodyCy} r={bodyR} fill={bodyDark} />
			</g>
		</Backdrop>
	);
};

export const AmberPlanet: React.FC = () => (
	<Planet
		spec={{
			sky: '#050403',
			bodyDark: '#7A4418',
			bodyMid: '#C8722E',
			bodyLight: '#F2C98A',
			rim: '#F5B45E',
			fluid: 'crater',
			seed: 21,
		}}
	/>
);

export const TealPlanet: React.FC = () => (
	<Planet
		spec={{
			sky: '#04141A',
			bodyDark: '#0A3A46',
			bodyMid: '#0E6E7E',
			bodyLight: '#7AC8C2',
			rim: '#E8874E',
			fluid: 'marble',
			seed: 33,
		}}
	/>
);

export const RedPlanet: React.FC = () => (
	<Planet
		spec={{
			sky: '#0E0A08',
			bodyDark: '#6E2E16',
			bodyMid: '#B85C28',
			bodyLight: '#E8A86A',
			rim: '#F2C98A',
			fluid: 'paint',
			seed: 47,
			horizon: 0.5,
		}}
	/>
);

export const InkPlanet: React.FC = () => (
	<Planet
		spec={{
			sky: '#0A0A0A',
			bodyDark: '#3A3A3A',
			bodyMid: '#B9B9B4',
			bodyLight: '#EFEFEA',
			rim: '#FFFFFF',
			rimWidth: 10,
			fluid: 'marble',
			seed: 55,
		}}
	/>
);
