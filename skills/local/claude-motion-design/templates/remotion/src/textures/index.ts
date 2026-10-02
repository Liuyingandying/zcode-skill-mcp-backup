import React from 'react';
import { DawnLimb } from './DawnLimb';
import { AmberPlanet, TealPlanet, RedPlanet, InkPlanet } from './Planet';
import { AmberCrust, Batik, GoldDust, EmberField, Blueprint, CreamLeaf, PaperPrint } from './Surfaces';

export type TextureId =
	| 'dawn-limb'
	| 'amber-crust'
	| 'amber-planet'
	| 'teal-planet'
	| 'red-planet'
	| 'ink-planet'
	| 'batik'
	| 'gold-dust'
	| 'ember-field'
	| 'blueprint'
	| 'cream-leaf'
	| 'paper-print';

/** Registry: timeline.ts refers to textures by id only. */
export const textures: Record<TextureId, React.FC> = {
	'dawn-limb': DawnLimb,
	'amber-crust': AmberCrust,
	'amber-planet': AmberPlanet,
	'teal-planet': TealPlanet,
	'red-planet': RedPlanet,
	'ink-planet': InkPlanet,
	batik: Batik,
	'gold-dust': GoldDust,
	'ember-field': EmberField,
	blueprint: Blueprint,
	'cream-leaf': CreamLeaf,
	'paper-print': PaperPrint,
};
