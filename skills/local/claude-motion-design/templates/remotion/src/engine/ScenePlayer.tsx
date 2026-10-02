import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile, interpolate, Easing } from 'remotion';
import timelineDefault from '../../content/scenes.default.json';
import { theme } from '../styles/theme';
import { PhotoScene, YearCardScene, BrandEndcard, TextureScene } from '../scenes/scenes';
import { SerifLine } from 'claude-motion-core';
import { MapPathScene, type MapRoute } from '../scenes/MapPathScene';
import { SvgSceneHost } from '../scenes/SvgScenes';

/**
 * ScenePlayer — the grammar engine. It plays a content JSON:
 * four scene kinds (texture / photo / yearCard / endcard), hard cuts by
 * default, optional BGM with drop automation. Visual decisions live in the
 * components; content decisions live in the JSON. Do not add scene kinds
 * without updating references/shot_grammar.md.
 */

export type Scene = {
	id: string;
	phase?: string;
	kind: 'texture' | 'photo' | 'yearCard' | 'endcard' | 'mapPath' | 'svg';
	texture?: string;
	photo?: string;
	start: number;
	end: number;
	camera?: { amount?: number; driftX?: number };
	archival?: boolean;
	year?: string;
	title?: string;
	caption?: string;
	route?: MapRoute;
	svg?: string;
	params?: Record<string, unknown>;
	photoCrop?: { x: number; y: number; w: number; h: number };
	sub?: string;
	motto?: string;
	yearRange?: string;
	text?: { lines: string[]; enterAt: number; style?: string };
};

export type Timeline = {
	meta: { title: string; fps: number; width: number; height: number; totalFrames: number };
	brand?: { nameCn?: string; nameEn?: string; motto?: string; yearRange?: string };
	audio?: { track?: string; volumeCurve?: { base: number; dropAt: number; dropTo: number; fadeOutFrom: number } };
	narration?: {
		text: string;
		enterAt: number;
		exitAt?: number;
		fontSize?: number;
		centerY?: number;
		letterSpacing?: string;
		weight?: number;
	}[];
	scenes: Scene[];
};

const TIMELINE_DEFAULT = timelineDefault as unknown as Timeline;
export const TIMELINE = TIMELINE_DEFAULT;

/**
 * ScenePlayer accepts an injected Timeline (instances) or falls back to the
 * template default content. Content layer is always external to the engine.
 */
export const ScenePlayer: React.FC<{ timeline?: Timeline }> = ({ timeline: injected }) => {
	const tl = injected ?? TIMELINE_DEFAULT;
	const scenes = tl.scenes;
	const audio = tl.audio;

	const bgmVolume = (frame: number): number => {
		if (!audio?.volumeCurve) return 1;
		const { base, dropAt, dropTo, fadeOutFrom } = audio.volumeCurve;
		if (frame < dropAt) return base;
		if (frame < dropAt + 18) {
			return interpolate(frame, [dropAt, dropAt + 18], [base, dropTo], {
				easing: Easing.out(Easing.quad),
				extrapolateLeft: 'clamp',
				extrapolateRight: 'clamp',
			});
		}
		if (frame > fadeOutFrom) {
			return interpolate(frame, [fadeOutFrom, tl.meta.totalFrames - 1], [dropTo, 0], {
				extrapolateLeft: 'clamp',
				extrapolateRight: 'clamp',
			});
		}
		return dropTo;
	};

	const renderScene = (s: Scene) => {
		const duration = s.end - s.start;
		switch (s.kind) {
			case 'photo':
				return (
					<PhotoScene
						photo={s.photo!}
						durationInFrames={duration}
						camera={s.camera}
						archival={s.archival}
						title={s.title}
						caption={s.caption}
						year={s.year}
						textLines={s.text?.lines ?? []}
						textEnterAt={s.text?.enterAt ? s.text.enterAt - s.start : 40}
						photoCrop={s.photoCrop}
					/>
				);
			case 'yearCard':
				return (
					<YearCardScene
						texture={s.texture!}
						durationInFrames={duration}
						camera={s.camera}
						year={s.year!}
						name={s.title ?? ''}
						textLines={s.text?.lines ?? []}
						textEnterAt={(s.text?.enterAt ?? s.start + 60) - s.start}
					/>
				);
			case 'endcard':
				return (
					<BrandEndcard
						durationInFrames={duration}
						title={s.title ?? tl.brand?.nameCn ?? ''}
						sub={s.sub ?? tl.brand?.nameEn ?? ''}
						motto={s.motto ?? tl.brand?.motto ?? ''}
						yearRange={s.yearRange ?? tl.brand?.yearRange ?? ''}
					/>
				);
			case 'mapPath':
				return (
					<MapPathScene
						durationInFrames={duration}
						route={s.route!}
						title={s.title}
						caption={s.caption}
						textEnterAt={s.text?.enterAt ? s.text.enterAt - s.start : 30}
					/>
				);
			case 'svg':
				return <SvgSceneHost id={s.svg!} durationInFrames={duration} params={s.params} />;
			case 'texture':
			default:
				return (
					<TextureScene
						texture={s.texture!}
						durationInFrames={duration}
						camera={s.camera}
						textLines={s.text?.lines ?? []}
						textEnterAt={(s.text?.enterAt ?? s.start + 60) - s.start}
					/>
				);
		}
	};

	return (
		<AbsoluteFill style={{ backgroundColor: theme.colors.deepSpace }}>
			{scenes.map((s) => (
				<Sequence key={s.id} from={s.start} durationInFrames={s.end - s.start} layout="none" name={s.id}>
					{renderScene(s)}
				</Sequence>
			))}
			{(tl.narration ?? []).map((n, i) => (
				<SerifLine
					key={`n${i}`}
					text={n.text}
					enterAt={n.enterAt}
					exitAt={n.exitAt}
					fontSize={n.fontSize}
					centerY={n.centerY}
					letterSpacing={n.letterSpacing}
					weight={n.weight}
				/>
			))}
			{audio?.track ? <Audio src={staticFile(audio.track)} volume={bgmVolume} /> : null}
		</AbsoluteFill>
	);
};
