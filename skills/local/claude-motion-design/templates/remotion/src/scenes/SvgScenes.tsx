import React from 'react';
import { AbsoluteFill } from 'remotion';
import { theme } from '../styles/theme';

/**
 * SvgSceneHost — instance-level SVG scene registry hook.
 * The engine's `svg` scene kind routes here; instances REPLACE this file
 * with their own registry (pure SVG + interpolate/spring scenes).
 * Keep drawings instance-side: this file in the template is only the contract.
 */

export type SvgSceneProps = {
	durationInFrames: number;
	params?: Record<string, unknown>;
};

export const svgSceneRegistry: Record<string, React.FC<SvgSceneProps>> = {};

export const SvgSceneHost: React.FC<{ id: string; durationInFrames: number; params?: Record<string, unknown> }> = ({
	id,
}) => (
	<AbsoluteFill style={{ backgroundColor: '#0A0E12', justifyContent: 'center', alignItems: 'center' }}>
		<div style={{ color: theme.colors.ivory, fontFamily: theme.fonts.mono }}>
			svg scene "{id}" not registered — override src/scenes/SvgScenes.tsx in your instance
		</div>
	</AbsoluteFill>
);
