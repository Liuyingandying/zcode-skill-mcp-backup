import React from 'react';
import { Composition } from 'remotion';
import { ScenePlayer, TIMELINE } from './engine/ScenePlayer';

/**
 * Root — single composition "Film", fully driven by content/scenes.json.
 * Change the JSON, not this file.
 */
export const RemotionRoot: React.FC = () => (
	<Composition
		id="Film"
		component={ScenePlayer}
		durationInFrames={TIMELINE.meta.totalFrames}
		fps={TIMELINE.meta.fps}
		width={TIMELINE.meta.width}
		height={TIMELINE.meta.height}
	/>
);
