import React from 'react';

/**
 * Shared helpers for procedural textures.
 * Every texture is a full-bleed 1920x1080 SVG; feTurbulence provides the
 * organic macro-photography feel with fixed seeds (deterministic renders).
 * A subtle per-frame drift of the noise layer gives the "alive" quality
 * the reference film gets from real fluids.
 */

export const W = 1920;
export const H = 1080;

export const frameDrift = (frame: number, amp: number, period: number) =>
	Math.sin((frame / period) * Math.PI * 2) * amp;

/**
 * Organic-edge displacement filter: roughens whatever it is applied to.
 */
export const RoughFilter: React.FC<{
	id: string;
	scale: number;
	seed: number;
	freq?: string;
	octaves?: number;
}> = ({ id, scale, seed, freq = '0.008 0.014', octaves = 3 }) => (
	<filter id={id} x="-20%" y="-20%" width="140%" height="140%">
		<feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={octaves} seed={seed} result="n" />
		<feDisplacementMap in="SourceGraphic" in2="n" scale={scale} xChannelSelector="R" yChannelSelector="G" />
	</filter>
);

/**
 * Grainy surface: luminance of a turbulence field, used as multiply overlay.
 */
export const GrainFilter: React.FC<{
	id: string;
	seed: number;
	freq?: string;
	octaves?: number;
}> = ({ id, seed, freq = '0.02 0.03', octaves = 4 }) => (
	<filter id={id} x="0%" y="0%" width="100%" height="100%">
		<feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={octaves} seed={seed} />
		<feColorMatrix
			type="matrix"
			values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.6 0.6 0.6 0 -0.55"
		/>
	</filter>
);

/**
 * Full-bleed backdrop every texture composes into.
 */
export const Backdrop: React.FC<{ children: React.ReactNode }> = ({ children }) => (
	<svg
		width={W}
		height={H}
		viewBox={`0 0 ${W} ${H}`}
		preserveAspectRatio="xMidYMid slice"
		style={{ display: 'block', width: '100%', height: '100%' }}
	>
		{children}
	</svg>
);
