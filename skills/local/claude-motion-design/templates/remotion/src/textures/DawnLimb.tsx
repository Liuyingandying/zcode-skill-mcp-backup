import React from 'react';
import { useCurrentFrame } from 'remotion';
import { Backdrop, W, H, frameDrift } from './kit';
import { theme } from '../styles/theme';

/**
 * DawnLimb — the opening (and ending) shot: a planetary terminator seen at
 * dawn. Navy sky -> cyan band -> amber band -> red rim, over a near-black
 * ground. The signature image of the reference film, rebuilt from gradients.
 */
export const DawnLimb: React.FC<{ seed?: number; rim?: string }> = ({
	seed = 7,
	rim = theme.colors.emberRed,
}) => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 10, 240); // slow lateral breathing of the glow
	return (
		<Backdrop>
			<defs>
				<linearGradient id="dl-sky" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#0A1220" />
					<stop offset="0.3" stopColor="#16324A" />
					<stop offset="0.46" stopColor="#2E6E86" />
					<stop offset="0.55" stopColor="#C8722E" />
					<stop offset="0.62" stopColor={rim} />
					<stop offset="0.67" stopColor="#1A0E0A" />
					<stop offset="1" stopColor="#0B0705" />
				</linearGradient>
				<filter id={`dl-atmo-${seed}`} x="-30%" y="-30%" width="160%" height="160%">
					<feTurbulence type="fractalNoise" baseFrequency="0.004 0.012" numOctaves={3} seed={seed} result="n" />
					<feDisplacementMap in="SourceGraphic" in2="n" scale={26} xChannelSelector="R" yChannelSelector="G" />
					<feGaussianBlur stdDeviation="7" />
				</filter>
				<filter id={`dl-ground-${seed}`}>
					<feTurbulence type="fractalNoise" baseFrequency="0.006 0.02" numOctaves={4} seed={seed + 3} result="n" />
					<feColorMatrix
						in="n"
						type="matrix"
						values="0 0 0 0 0.05  0 0 0 0 0.04  0 0 0 0 0.035  0.9 0.9 0.9 0 -0.9"
					/>
				</filter>
			</defs>

			<rect width={W} height={H} fill="url(#dl-sky)" />
			{/* displaced glowing terminator line */}
			<g filter={`url(#dl-atmo-${seed})`} opacity={0.9}>
				<ellipse
					cx={W / 2 + drift}
					cy={H * 0.615}
					rx={W * 0.72}
					ry={H * 0.055}
					fill="none"
					stroke={rim}
					strokeWidth={26}
					opacity={0.85}
				/>
				<ellipse
					cx={W / 2 + drift * 1.3}
					cy={H * 0.6}
					rx={W * 0.5}
					ry={H * 0.05}
					fill="#E8A25C"
					opacity={0.35}
				/>
			</g>
			{/* crisp hot rim right at the terminator */}
			<path
				d={`M-40 ${H * 0.628} Q ${W / 2 + drift} ${H * 0.572} ${W + 40} ${H * 0.632}`}
				fill="none"
				stroke="#F5B45E"
				strokeWidth={5}
				opacity={0.95}
			/>
			{/* near-black ground swallowing the lower frame */}
			<path
				d={`M0 ${H * 0.63} Q ${W / 2 + drift} ${H * 0.575} ${W} ${H * 0.635} L ${W} ${H} L 0 ${H} Z`}
				fill="#0B0705"
			/>
			<rect width={W} height={H} filter={`url(#dl-ground-${seed})`} opacity={0.28} />
		</Backdrop>
	);
};
