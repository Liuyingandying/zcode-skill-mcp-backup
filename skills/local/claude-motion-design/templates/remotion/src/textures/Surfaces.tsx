import React from 'react';
import { useCurrentFrame } from 'remotion';
import { Backdrop, W, H, frameDrift, RoughFilter } from './kit';

/**
 * AmberCrust — long second shot: a backlit golden organic crust filling the
 * lower two thirds, dark air above, sparkling ridge crest.
 */
export const AmberCrust: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 12, 260);
	return (
		<Backdrop>
			<defs>
				<linearGradient id="ac-air" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#0C0A06" />
					<stop offset="1" stopColor="#241608" />
				</linearGradient>
				<linearGradient id="ac-body" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#EFD589" />
					<stop offset="0.3" stopColor="#D9A33B" />
					<stop offset="0.75" stopColor="#8A5A22" />
					<stop offset="1" stopColor="#3A2408" />
				</linearGradient>
				<RoughFilter id={`ac-rough`} scale={44} seed={13} freq="0.007 0.012" octaves={4} />
				<filter id="ac-grit" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.02 0.05" numOctaves={4} seed={19} />
					<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  1.2 1.2 1.2 0 -0.8" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id="ac-spark" x="-20%" y="-40%" width="140%" height="180%">
					<feGaussianBlur stdDeviation="9" />
				</filter>
			</defs>
			<rect width={W} height={H} fill="url(#ac-air)" />
			<g filter="url(#ac-rough)">
				<path
					d={`M-60 ${H * 0.42} Q ${W * 0.3 + drift} ${H * 0.3} ${W * 0.62} ${H * 0.4} T ${W + 60} ${H * 0.36} L ${W + 60} ${H + 60} L -60 ${H + 60} Z`}
					fill="url(#ac-body)"
				/>
			</g>
			<g filter="url(#ac-grit)" opacity={0.4}>
				<path
					d={`M-60 ${H * 0.42} Q ${W * 0.3 + drift} ${H * 0.3} ${W * 0.62} ${H * 0.4} T ${W + 60} ${H * 0.36} L ${W + 60} ${H + 60} L -60 ${H + 60} Z`}
					fill="#000"
				/>
			</g>
			{/* crest light — soft, not a synthetic stroke */}
			<g filter="url(#ac-spark)" opacity={0.55}>
				<path
					d={`M-60 ${H * 0.42} Q ${W * 0.3 + drift} ${H * 0.3} ${W * 0.62} ${H * 0.4} T ${W + 60} ${H * 0.36}`}
					fill="none"
					stroke="#F5D98A"
					strokeWidth={16}
				/>
			</g>
		</Backdrop>
	);
};

/**
 * Batik — teal speckled field with a red patterned band, rough textile edge.
 */
export const Batik: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 8, 200);
	return (
		<Backdrop>
			<defs>
				<linearGradient id="bk-top" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#5E1A20" />
					<stop offset="0.8" stopColor="#8A2438" />
					<stop offset="1" stopColor="#3A6A4E" />
				</linearGradient>
				<filter id="bk-speckle" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.09 0.11" numOctaves={2} seed={61} />
					<feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.95  0 0 0 0 0.72  1.4 1.4 1.4 0 -1.05" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id="bk-weave" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="turbulence" baseFrequency="0.012 0.16" numOctaves={2} seed={67} />
					<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.8 0.8 0.8 0 -0.62" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<RoughFilter id="bk-edge" scale={14} seed={71} freq="0.01 0.02" octaves={3} />
			</defs>
			<rect width={W} height={H} fill="#1E7A62" />
			{/* speckled teal field */}
			<rect width={W} height={H} filter="url(#bk-speckle)" opacity={0.85} />
			{/* red patterned band across the upper third */}
			<g filter="url(#bk-edge)">
				<path
					d={`M-40 ${H * 0.34} Q ${W * 0.25 + drift} ${H * 0.24} ${W * 0.55} ${H * 0.32} T ${W + 40} ${H * 0.26} L ${W + 40} -40 L -40 -40 Z`}
					fill="url(#bk-top)"
				/>
			</g>
			{/* weave shadow inside the band */}
			<g filter="url(#bk-weave)" opacity={0.5}>
				<path
					d={`M-40 ${H * 0.34} Q ${W * 0.25 + drift} ${H * 0.24} ${W * 0.55} ${H * 0.32} T ${W + 40} ${H * 0.26} L ${W + 40} -40 L -40 -40 Z`}
					fill="#000"
				/>
			</g>
		</Backdrop>
	);
};

/**
 * GoldDust — granular golden field glowing against the dark.
 */
export const GoldDust: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 16, 280);
	return (
		<Backdrop>
			<defs>
				<radialGradient id="gd-glow" cx="0.5" cy="0.78" r="0.62">
					<stop offset="0" stopColor="#C89B3C" />
					<stop offset="0.35" stopColor="#6E4E18" />
					<stop offset="0.7" stopColor="#241806" />
					<stop offset="1" stopColor="#0A0703" />
				</radialGradient>
				<filter id="gd-grain" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.11 0.11" numOctaves={3} seed={83} />
					<feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 0.8  0 0 0 0 0.42  2.0 0 0 0 -1.28" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id="gd-clumps" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.016 0.02" numOctaves={4} seed={89} />
					<feColorMatrix type="matrix" values="0 0 0 0 0.03  0 0 0 0 0.02  0 0 0 0 0.01  2.6 0 0 0 -1.8" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
			</defs>
			<rect width={W} height={H} fill="url(#gd-glow)" />
			<g transform={`translate(${drift * 0.6}, ${-drift * 0.25})`}>
				<rect x={-40} y={-40} width={W + 80} height={H + 80} filter="url(#gd-clumps)" opacity={0.8} />
			</g>
			<rect width={W} height={H} filter="url(#gd-grain)" opacity={0.9} />
		</Backdrop>
	);
};

/**
 * EmberField — horizontal bands of smouldering red/orange noise on black.
 */
export const EmberField: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 10, 220);
	return (
		<Backdrop>
			<defs>
				<filter id="ef-bands" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="turbulence" baseFrequency="0.006 0.11" numOctaves={4} seed={97} />
					<feColorMatrix
						type="matrix"
						values="0 0 0 0 0.82  0 0 0 0 0.34  0 0 0 0 0.11  2.4 0 0 0 -1.05"
					/>
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id="ef-heat" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.004 0.045" numOctaves={5} seed={101} />
					<feColorMatrix
						type="matrix"
						values="0 0 0 0 1  0 0 0 0 0.58  0 0 0 0 0.22  2.2 0 0 0 -0.95"
					/>
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<radialGradient id="ef-vig" cx="0.5" cy="0.55" r="0.8">
					<stop offset="0.5" stopColor="#000" stopOpacity="0" />
					<stop offset="1" stopColor="#000" stopOpacity="0.75" />
				</radialGradient>
			</defs>
			<rect width={W} height={H} fill="#160704" />
			<g transform={`translate(${drift}, 0)`}>
				<rect x={-30} width={W + 60} height={H} filter="url(#ef-bands)" opacity={0.9} />
			</g>
			<rect width={W} height={H} filter="url(#ef-heat)" opacity={0.65} />
			<rect width={W} height={H} fill="url(#ef-vig)" />
		</Backdrop>
	);
};

/**
 * Blueprint — white technical arcs on slate blue (the one cool-toned shot).
 */
export const Blueprint: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 6, 300);
	const arcs = [0.18, 0.3, 0.44, 0.6, 0.78];
	return (
		<Backdrop>
			<defs>
				<linearGradient id="bp-bg" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#26436B" />
					<stop offset="1" stopColor="#142C48" />
				</linearGradient>
				<filter id="bp-soft">
					<feGaussianBlur stdDeviation="1.1" />
				</filter>
			</defs>
			<rect width={W} height={H} fill="url(#bp-bg)" />
			<g filter="url(#bp-soft)" stroke="#DCE8F2" fill="none" opacity={0.85}>
				{arcs.map((r, i) => (
					<circle
						key={i}
						cx={W * 0.5 + drift}
						cy={H * 1.35}
						r={W * r * 0.9}
						strokeWidth={i % 2 === 0 ? 3 : 1.5}
						opacity={0.5 + i * 0.08}
					/>
				))}
				{/* radial tick lines */}
				{Array.from({ length: 18 }).map((_, i) => {
					const a = (i / 18) * Math.PI * 2;
					const x1 = W * 0.5 + drift + Math.cos(a) * W * 0.18 * 0.9;
					const y1 = H * 1.35 + Math.sin(a) * W * 0.18 * 0.9;
					const x2 = W * 0.5 + drift + Math.cos(a) * W * 0.78 * 0.9;
					const y2 = H * 1.35 + Math.sin(a) * W * 0.78 * 0.9;
					return <line key={`t${i}`} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth={0.8} opacity={0.28} />;
				})}
			</g>
		</Backdrop>
	);
};

/**
 * CreamLeaf — the one light shot: green organic mass on warm cream paper.
 */
export const CreamLeaf: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 9, 260);
	return (
		<Backdrop>
			<defs>
				<linearGradient id="cl-paper" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#EFE9DA" />
					<stop offset="1" stopColor="#E2DAC6" />
				</linearGradient>
				<linearGradient id="cl-leaf" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#8FAE5E" />
					<stop offset="0.5" stopColor="#5E7E3A" />
					<stop offset="1" stopColor="#3A5424" />
				</linearGradient>
				<RoughFilter id="cl-edge" scale={26} seed={103} freq="0.006 0.012" octaves={3} />
				<filter id="cl-veins" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.012 0.05" numOctaves={3} seed={107} />
					<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.9 0.9 0.9 0 -0.68" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<filter id="cl-tooth" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.2 0.2" numOctaves={2} seed={109} />
					<feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.5  0 0 0 0 0.4  0.7 0.7 0.7 0 -0.5" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
			</defs>
			<rect width={W} height={H} fill="url(#cl-paper)" />
			<rect width={W} height={H} filter="url(#cl-tooth)" opacity={0.35} />
			{/* asymmetric leaf mass: rises from lower-left, high shoulder left-of-center */}
			<g filter="url(#cl-edge)">
				<path
					d={`M-60 ${H * 0.62} Q ${W * 0.18 + drift} ${H * 0.4} ${W * 0.42} ${H * 0.47} Q ${W * 0.68 + drift * 0.5} ${H * 0.55} ${W + 60} ${H * 0.72} L ${W + 60} ${H + 60} L -60 ${H + 60} Z`}
					fill="url(#cl-leaf)"
				/>
			</g>
			<g filter="url(#cl-veins)" opacity={0.55}>
				<path
					d={`M-60 ${H * 0.62} Q ${W * 0.18 + drift} ${H * 0.4} ${W * 0.42} ${H * 0.47} Q ${W * 0.68 + drift * 0.5} ${H * 0.55} ${W + 60} ${H * 0.72} L ${W + 60} ${H + 60} L -60 ${H + 60} Z`}
					fill="#2E4418"
				/>
			</g>
			{/* midrib veins radiating across the leaf — clipped to the mass */}
			<clipPath id="cl-leafclip">
				<path
					d={`M-60 ${H * 0.62} Q ${W * 0.18 + drift} ${H * 0.4} ${W * 0.42} ${H * 0.47} Q ${W * 0.68 + drift * 0.5} ${H * 0.55} ${W + 60} ${H * 0.72} L ${W + 60} ${H + 60} L -60 ${H + 60} Z`}
				/>
			</clipPath>
			<g clipPath="url(#cl-leafclip)">
				<g stroke="#3E5A24" strokeWidth={2.5} opacity={0.4} fill="none">
					{Array.from({ length: 7 }).map((_, i) => {
						const x0 = W * (0.04 + i * 0.13);
						return (
							<path
								key={i}
								d={`M ${W * 0.2 + drift} ${H * 0.72} Q ${(x0 + W * 0.2) / 2} ${H * 0.6} ${x0} ${H * (0.52 + (i % 3) * 0.05)}`}
							/>
						);
					})}
				</g>
			</g>
		</Backdrop>
	);
};

/**
 * PaperPrint — B&W etched mass on cream (motion-study print vibe).
 */
export const PaperPrint: React.FC = () => {
	const frame = useCurrentFrame();
	const drift = frameDrift(frame, 7, 240);
	return (
		<Backdrop>
			<defs>
				<linearGradient id="pp-paper" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" stopColor="#EAE2CE" />
					<stop offset="1" stopColor="#D8CEB4" />
				</linearGradient>
				<filter id="pp-etch" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="turbulence" baseFrequency="0.006 0.09" numOctaves={4} seed={113} />
					<feColorMatrix type="matrix" values="0 0 0 0 0.16  0 0 0 0 0.13  0 0 0 0 0.09  1.2 1.2 1.2 0 -0.7" />
					<feComposite operator="in" in2="SourceGraphic" />
				</filter>
				<RoughFilter id="pp-mass" scale={38} seed={127} freq="0.008 0.018" octaves={4} />
			</defs>
			<rect width={W} height={H} fill="url(#pp-paper)" />
			<g filter="url(#pp-mass)">
				<ellipse cx={W * 0.5 + drift} cy={H * 0.55} rx={W * 0.56} ry={H * 0.3} fill="#3A3428" opacity={0.85} />
			</g>
			<g filter="url(#pp-etch)" opacity={0.7}>
				<ellipse cx={W * 0.5 + drift} cy={H * 0.55} rx={W * 0.56} ry={H * 0.3} fill="#1A1710" />
			</g>
			{/* horizon rule, printed */}
			<rect x={0} y={H * 0.78} width={W} height={3} fill="#3A3428" opacity={0.5} />
		</Backdrop>
	);
};
