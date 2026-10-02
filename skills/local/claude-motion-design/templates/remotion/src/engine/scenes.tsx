import React from 'react';
import {
	AbsoluteFill,
	Img,
	staticFile,
	useCurrentFrame,
	interpolate,
	Easing,
} from 'remotion';
import { theme } from '../styles/theme';
import { textures } from '../textures';
import { W, H } from '../textures/kit';
import { FilmGrain, Vignette, SerifLine } from 'claude-motion-core';

/**
 * PhotoScene — archival photograph, Ken Burns push, depth via a blurred
 * ambient twin drifting at a different rate (2.5D parallax without warping
 * history), archival grade (sepia/contrast/heavier grain), serif title +
 * spaced caption. Text layer is dead still; only the photograph breathes.
 */
export const PhotoScene: React.FC<{
	photo: string;
	durationInFrames: number;
	camera?: { amount?: number; driftX?: number };
	archival?: boolean;
	title?: string;
	caption?: string;
	year?: string;
	textLines?: string[];
	textLineCenterY?: number;
	textEnterAt?: number;
	photoCrop?: { x: number; y: number; w: number; h: number };
}> = ({ photo, durationInFrames, camera, archival = false, title, caption, year, textLines = [], textLineCenterY, textEnterAt = 40, photoCrop }) => {
	// spirit lines live above the title block when both are present
	const resolvedLineY = textLineCenterY ?? (title ? 0.3 : 0.42);
	const frame = useCurrentFrame();
	// photoCrop: start the framing INSIDE the normalized rect (e.g. the wax
	// seal). Implemented with transform-origin at the crop center + scale =
	// 1/rect — exact framing, no translate-percent pitfalls.
	const origin = photoCrop
		? `${((photoCrop.x + photoCrop.w / 2) * 100).toFixed(2)}% ${((photoCrop.y + photoCrop.h / 2) * 100).toFixed(2)}%`
		: '50% 50%';
	// fill the frame from the crop rect: scale = max(frameAspectFit) — the
	// larger ratio guarantees the rect covers the whole 16:9 frame.
	const cropScale = photoCrop ? Math.max(W / (photoCrop.w * W), H / (photoCrop.h * H)) : 1;
	const parallaxScale = interpolate(frame, [0, durationInFrames], [1.12 * cropScale, 1.2 * cropScale], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const parallaxX = interpolate(frame, [0, durationInFrames], [0, -(camera?.driftX ?? 0) * 1.6], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const filter = archival
		? `sepia(${theme.motion.archivalSepia}) contrast(${theme.motion.archivalContrast}) brightness(0.96)`
		: 'none';
	const grainOpacity = archival ? theme.motion.archivalGrainOpacity : theme.motion.grainOpacity;

	// title/caption rise in with the pop grammar
	const tIn = (at: number) =>
		interpolate(frame - at, [0, theme.motion.textInFrames], [0, 1], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
			easing: Easing.out(Easing.quad),
		});
	const titleOp = title ? tIn(textEnterAt) : 0;
	const capOp = caption ? tIn(textEnterAt + 12) : 0;

	return (
		<AbsoluteFill style={{ backgroundColor: theme.colors.deepSpace }}>
			{/* depth layer: blurred ambient twin, counter-drifting */}
			<AbsoluteFill style={{ transform: `scale(${parallaxScale.toFixed(4)}) translate(${parallaxX.toFixed(2)}px, 0)`, transformOrigin: origin }}>
				<Img
					src={staticFile(`photos/${photo}`)}
					style={{
						width: '100%',
						height: '100%',
						objectFit: 'cover',
						filter: `${filter} blur(26px) brightness(0.5)`,
					}}
				/>
			</AbsoluteFill>
			{/* sharp plate: slow Ken Burns push */}
			<AbsoluteFill
				style={{
					transform: `scale(${(interpolate(
						frame,
						[0, durationInFrames],
						[1.0, 1.0 + (camera?.amount ?? 0.05)],
						{ extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
					) * cropScale).toFixed(4)}) translate(${((camera?.driftX ?? 0) * (frame / durationInFrames)).toFixed(2)}px, 0)`,
					transformOrigin: origin,
				}}
			>
				<Img
					src={staticFile(`photos/${photo}`)}
					style={{ width: '100%', height: '100%', objectFit: 'cover', filter }}
				/>
			</AbsoluteFill>

			<Vignette />
			{/* legibility band: a quiet scrim where the title/caption sit */}
			<AbsoluteFill
				style={{
					background:
						'linear-gradient(to bottom, rgba(6,8,10,0) 30%, rgba(6,8,10,0.34) 43%, rgba(6,8,10,0.34) 62%, rgba(6,8,10,0) 74%)',
				}}
			/>
			<FilmGrain opacity={grainOpacity} />

			{/* text block: anchored like the montage words, right above centre */}
			{year ? (
				<AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center' }}>
					<div
						style={{
							position: 'absolute',
							top: '26%',
							transform: 'translateY(-50%)',
							opacity: titleOp,
							fontFamily: theme.fonts.serif,
							fontSize: theme.type.yearBig.fontSize,
							fontWeight: theme.type.yearBig.weight,
							color: theme.colors.ivory,
							lineHeight: 1,
							textShadow: '0 4px 40px rgba(0,0,0,0.55)',
							letterSpacing: '0.04em',
						}}
					>
						{year}
					</div>
				</AbsoluteFill>
			) : null}
			{title ? (
				<AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center' }}>
					<div
						style={{
							position: 'absolute',
							top: year ? '47%' : `${theme.type.montage.centerY * 100}%`,
							transform: 'translateY(-50%)',
							opacity: titleOp,
							fontFamily: theme.fonts.serifCjk,
							fontSize: theme.type.photoTitle.fontSize,
							fontWeight: theme.type.photoTitle.weight,
							letterSpacing: theme.type.photoTitle.letterSpacing,
							color: theme.colors.ivory,
							lineHeight: 1.2,
							textShadow: '0 2px 30px rgba(0,0,0,0.55), 0 0 60px rgba(0,0,0,0.3)',
							whiteSpace: 'nowrap',
						}}
					>
						{title}
					</div>
				</AbsoluteFill>
			) : null}
			{caption ? (
				<AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center' }}>
					<div
						style={{
							position: 'absolute',
							top: year ? '58%' : `${theme.type.montage.centerY * 100 + 8.5}%`,
							transform: 'translateY(-50%)',
							opacity: capOp,
							fontFamily: theme.fonts.serifCjk,
							fontSize: theme.type.caption.fontSize,
							fontWeight: theme.type.caption.weight,
							letterSpacing: theme.type.caption.letterSpacing,
							color: 'rgba(240,238,228,0.82)',
							lineHeight: 1.5,
							textShadow: '0 2px 20px rgba(0,0,0,0.6)',
							whiteSpace: 'nowrap',
						}}
					>
						{caption}
					</div>
				</AbsoluteFill>
			) : null}
			{/* spirit lines: serif overlay text carried by the JSON */}
			{textLines.map((line, i) => (
				<SerifLine
					key={i}
					text={line}
					enterAt={textEnterAt + i * 14}
					fontSize={58}
					letterSpacing="0.2em"
					centerY={resolvedLineY + i * 0.1}
				/>
			))}
		</AbsoluteFill>
	);
};

/**
 * YearCardScene — texture + big serif year + name + optional small line.
 */
export const YearCardScene: React.FC<{
	texture: string;
	durationInFrames: number;
	camera?: { amount?: number };
	year: string;
	name: string;
	textLines?: string[];
	textEnterAt?: number;
}> = ({ texture, durationInFrames, camera, year, name, textLines = [], textEnterAt = 60 }) => {
	const Tex = textures[texture as keyof typeof textures];
	const frame = useCurrentFrame();
	const yIn = interpolate(frame, [8, 8 + theme.motion.textInFrames], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: Easing.out(Easing.quad),
	});
	const nIn = interpolate(frame, [20, 20 + theme.motion.textInFrames], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: Easing.out(Easing.quad),
	});
	const scaleIn = interpolate(frame, [8, 8 + theme.motion.textInFrames], [1.03, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: Easing.out(Easing.cubic),
	});
	const push = interpolate(frame, [0, durationInFrames], [1, 1 + (camera?.amount ?? 0.04)], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return (
		<AbsoluteFill style={{ backgroundColor: theme.colors.deepSpace }}>
			<AbsoluteFill style={{ transform: `scale(${push})` }}>
				<Tex />
			</AbsoluteFill>
			<Vignette />
			{/* legibility band behind the year + name */}
			<AbsoluteFill
				style={{
					background:
						'linear-gradient(to bottom, rgba(6,8,10,0) 22%, rgba(6,8,10,0.38) 36%, rgba(6,8,10,0.38) 62%, rgba(6,8,10,0) 76%)',
				}}
			/>
			<FilmGrain />
			<AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center' }}>
				<div
					style={{
						position: 'absolute',
						top: '34%',
						transform: `translateY(-50%) scale(${scaleIn})`,
						opacity: yIn,
						fontFamily: theme.fonts.serif,
						fontSize: theme.type.yearBig.fontSize,
						fontWeight: theme.type.yearBig.weight,
						letterSpacing: '0.05em',
						color: theme.colors.ivory,
						lineHeight: 1,
						textShadow: '0 4px 44px rgba(0,0,0,0.75), 0 0 80px rgba(0,0,0,0.4)',
					}}
				>
					{year}
				</div>
				<div
					style={{
						position: 'absolute',
						top: '50%',
						transform: 'translateY(-50%)',
						opacity: nIn,
						fontFamily: theme.fonts.serifCjk,
						fontSize: 84,
						fontWeight: 600,
						letterSpacing: '0.3em',
						textIndent: '0.3em',
						color: theme.colors.ivory,
						textShadow: '0 2px 34px rgba(0,0,0,0.75), 0 0 60px rgba(0,0,0,0.45)',
					}}
				>
					{name}
				</div>
			</AbsoluteFill>
			{textLines.map((line, i) => (
				<SerifLine
					key={i}
					text={line}
					enterAt={textEnterAt + i * 10}
					fontSize={52}
					letterSpacing="0.22em"
					centerY={0.68}
				/>
			))}
		</AbsoluteFill>
	);
};

/**
 * BrandEndcard — the brand lockup: atmospheric card, big brand name, English
 * wordmark, motto with seal-red accent, year range, dawn glow breathing.
 */
export const BrandEndcard: React.FC<{
	durationInFrames: number;
	title: string;
	sub: string;
	motto: string;
	yearRange: string;
}> = ({ durationInFrames, title, sub, motto, yearRange }) => {
	const frame = useCurrentFrame();
	const breathe = Math.sin(frame / 52) * 0.06 + Math.sin(frame / 23) * 0.02;
	const tIn = (at: number) =>
		interpolate(frame - at, [0, theme.motion.textInFrames], [0, 1], {
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
			easing: Easing.out(Easing.quad),
		});
	return (
		<AbsoluteFill style={{ backgroundColor: theme.colors.endcardNavy }}>
			<AbsoluteFill
				style={{
					background: `radial-gradient(120% 62% at 50% 118%, rgba(78,142,168,${0.5 + breathe}) 0%, rgba(44,90,116,${
						0.32 + breathe * 0.6
					}) 34%, rgba(20,42,58,0.16) 62%, rgba(11,17,26,0) 82%)`,
				}}
			/>
			{/* warm dawn accent on the glow, echoing the film's close */}
			<AbsoluteFill
				style={{
					background: `radial-gradient(80% 30% at 50% 112%, rgba(200,114,46,${0.22 + breathe * 0.4}) 0%, rgba(200,114,46,0) 100%)`,
				}}
			/>
			<AbsoluteFill style={{ alignItems: 'center' }}>
				<div
					style={{
						position: 'absolute',
						top: '36%',
						transform: 'translateY(-50%)',
						opacity: tIn(12),
						fontFamily: theme.fonts.serifCjk,
						fontSize: theme.type.endcard.titleSize,
						fontWeight: 600,
						letterSpacing: '0.18em',
						textIndent: '0.18em',
						color: theme.colors.ivory,
						lineHeight: 1,
						textShadow: '0 4px 44px rgba(0,0,0,0.5)',
					}}
				>
					{title}
				</div>
				<div
					style={{
						position: 'absolute',
						top: '47%',
						transform: 'translateY(-50%)',
						opacity: tIn(22),
						fontFamily: theme.fonts.mono,
						fontSize: theme.type.endcard.subSize,
						fontWeight: 400,
						letterSpacing: '0.5em',
						textIndent: '0.5em',
						color: 'rgba(240,238,228,0.66)',
					}}
				>
					{sub}
				</div>
				{/* motto row with seal-red separators */}
				<div
					style={{
						position: 'absolute',
						top: '58%',
						transform: 'translateY(-50%)',
						opacity: tIn(34),
						display: 'flex',
						alignItems: 'center',
						gap: 28,
					}}
				>
					<span
						style={{
							fontFamily: theme.fonts.serifCjk,
							fontSize: theme.type.endcard.mottoSize,
							fontWeight: 600,
							letterSpacing: '0.3em',
							color: theme.colors.ivory,
						}}
					>
						{motto}
					</span>
				</div>
				<div
					style={{
						position: 'absolute',
						top: '66%',
						transform: 'translateY(-50%)',
						opacity: tIn(44),
						fontFamily: theme.fonts.serif,
						fontSize: 36,
						letterSpacing: '0.28em',
						color: 'rgba(240,238,228,0.72)',
					}}
				>
					{yearRange}
				</div>
			</AbsoluteFill>
			<FilmGrain opacity={0.04} />
		</AbsoluteFill>
	);
};

/**
 * TextureScene — plain texture + optional serif line (opening / milestone).
 */
export const TextureScene: React.FC<{
	texture: string;
	durationInFrames: number;
	camera?: { amount?: number };
	textLines?: string[];
	textEnterAt?: number;
	exitAt?: number;
}> = ({ texture, durationInFrames, camera, textLines = [], textEnterAt = 60, exitAt }) => {
	const Tex = textures[texture as keyof typeof textures];
	const frame = useCurrentFrame();
	const push = interpolate(frame, [0, durationInFrames], [1, 1 + (camera?.amount ?? 0.05)], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	return (
		<AbsoluteFill style={{ backgroundColor: theme.colors.deepSpace }}>
			<AbsoluteFill style={{ transform: `scale(${push})` }}>
				<Tex />
			</AbsoluteFill>
			<Vignette />
			<FilmGrain />
			{textLines.map((line, i) => (
				<SerifLine
					key={i}
					text={line}
					enterAt={textEnterAt + i * 10}
					exitAt={exitAt}
					centerY={textLines.length > 1 ? 0.455 - (textLines.length - 1) * 0.05 + i * 0.1 : undefined}
				/>
			))}
		</AbsoluteFill>
	);
};
