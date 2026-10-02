import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { theme } from '../styles/theme';
import { W, H, frameDrift } from '../textures/kit';
import { AmbientBackdrop, FilmGrain, Vignette, SerifLine } from 'claude-motion-core';

/**
 * MapPathScene — content-type scene: a minimal schematic route map.
 * One dashed polyline drawn on over time, city nodes popping as the line
 * reaches them, mono labels, optional title. Coordinates normalized 0..1.
 */

export type MapRoute = {
	points: [number, number][]; // normalized [x, y]
	labels: { name: string; sub?: string }[];
};

export const MapPathScene: React.FC<{
	durationInFrames: number;
	route: MapRoute;
	title?: string;
	caption?: string;
	textEnterAt?: number;
}> = ({ durationInFrames, route, title, caption, textEnterAt = 30 }) => {
	const frame = useCurrentFrame();

	const pts = route.points.map(([x, y]) => [x * W, y * H] as [number, number]);

	const segLens: number[] = [];
	let total = 0;
	for (let i = 1; i < pts.length; i++) {
		const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
		segLens.push(l);
		total += l;
	}
	const nodeAt = [0, ...segLens.map((l, i) => segLens.slice(0, i + 1).reduce((a, b) => a + b, 0) / total)];

	const drawStart = 18;
	const drawEnd = Math.round(durationInFrames * 0.72);
	const progress = interpolate(frame, [drawStart, drawEnd], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	const pointAt = (p: number): [number, number] => {
		const dist = p * total;
		let acc = 0;
		for (let i = 0; i < segLens.length; i++) {
			if (dist <= acc + segLens[i] || i === segLens.length - 1) {
				const t = Math.min(1, Math.max(0, (dist - acc) / segLens[i]));
				return [
					pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
					pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t,
				];
			}
			acc += segLens[i];
		}
		return pts[pts.length - 1];
	};

	const tip = pointAt(progress);
	const dashLen = total * 1.2;

	return (
		<AbsoluteFill>
			<AbsoluteFill style={{ backgroundColor: theme.colors.slate }} />
			<svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>
				<polyline
					points={pts.map((p) => p.join(',')).join(' ')}
					fill="none"
					stroke="rgba(240,238,228,0.16)"
					strokeWidth={2}
					strokeDasharray="4 10"
				/>
				<polyline
					points={pts.map((p) => p.join(',')).join(' ')}
					fill="none"
					stroke={theme.colors.amberBright}
					strokeWidth={3.5}
					strokeDasharray={`${dashLen}`}
					strokeDashoffset={dashLen * (1 - progress)}
					strokeLinecap="round"
					style={{ filter: 'drop-shadow(0 0 8px rgba(232,162,92,0.55))' }}
				/>
				{progress > 0.01 && progress < 1 && (
					<circle cx={tip[0]} cy={tip[1]} r={6} fill={theme.colors.ivory} opacity={0.9} />
				)}
				{pts.map((p, i) => {
					const reach = nodeAt[i];
					const shown = progress >= reach - 0.001 ? 1 : 0;
					const appearFrame = drawStart + (drawEnd - drawStart) * reach;
					const pop = interpolate(frame, [appearFrame, appearFrame + 8], [0, 1], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					});
					const label = route.labels[i];
					const dx = p[0] > W * 0.6 ? -1 : 1;
					return (
						<g key={i} opacity={shown * pop}>
							<circle cx={p[0]} cy={p[1]} r={7} fill={theme.colors.sealRed} />
							<circle cx={p[0]} cy={p[1]} r={13} fill="none" stroke={theme.colors.ivory} strokeWidth={1.2} opacity={0.6} />
							<text x={p[0] + dx * 24} y={p[1] - 26} textAnchor={dx > 0 ? 'start' : 'end'} fill={theme.colors.ivory} style={{ fontFamily: theme.fonts.serifCjk, fontSize: 34, fontWeight: 600 }}>
								{label.name}
							</text>
							{label.sub ? (
								<text x={p[0] + dx * 24} y={p[1] + 44} textAnchor={dx > 0 ? 'start' : 'end'} fill="rgba(240,238,228,0.72)" style={{ fontFamily: theme.fonts.serifCjk, fontSize: 22, letterSpacing: 2 }}>
									{label.sub}
								</text>
							) : null}
						</g>
					);
				})}
			</svg>
			{title ? <SerifLine text={title} enterAt={textEnterAt} fontSize={78} centerY={0.14} /> : null}
			{caption ? (
				<SerifLine
					text={caption}
					enterAt={textEnterAt + 14}
					fontSize={30}
					letterSpacing="0.24em"
					color="rgba(240,238,228,0.8)"
					centerY={0.2}
				/>
			) : null}
			<FilmGrain />
			<Vignette />
			<AbsoluteFill style={{ transform: `translate(${frameDrift(frame, 4, 260)}px, 0)` }} />
		</AbsoluteFill>
	);
};
