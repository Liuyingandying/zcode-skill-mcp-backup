import path from 'path';
import { Config } from '@remotion/cli/config';

// claude-motion-core is linked as a file: dependency; point the bundle at
// the host single copy. NOTE: remotion.config executes from the CLI dist —
// use process.cwd(), never __dirname.
const projectRoot = process.cwd();
const hostModules = path.join(projectRoot, 'node_modules');
const coreDepth = '../..'.repeat(4); // templates/remotion -> workspace root

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setChromiumDisableWebSecurity(true);

Config.overrideWebpackConfig((c) => ({
	...c,
	resolve: {
		...c.resolve,
		alias: {
			...(c.resolve?.alias ?? {}),
			'claude-motion-core': path.join(projectRoot, coreDepth, 'claude-motion-core', 'src', 'index.ts'),
		},
	},
}));
