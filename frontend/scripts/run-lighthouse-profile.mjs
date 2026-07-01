import { spawn, spawnSync } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const DEFAULT_BASE_URL = 'http://127.0.0.1:4173';
const DEFAULT_TARGET_PATH = '/?q=mobilite&sort=quality_desc&page=1&fmt=CSV&tag=mobilite';
const DEFAULT_OUTPUT_DIR = './reports/lighthouse';
const LIGHTHOUSE_BINARY = process.platform === 'win32' ? 'lighthouse.cmd' : 'lighthouse';
const DEFAULT_SERVER_READY_TIMEOUT_MS = 10_000;

function findBrowserExecutable() {
	const candidates =
		process.platform === 'win32'
			? ['chrome', 'msedge']
			: ['google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium', 'vivaldi', 'vivaldi-stable'];

	for (const candidate of candidates) {
		const result = spawnSync('which', [candidate], { encoding: 'utf-8' });
		if (result.status === 0) {
			const resolved = result.stdout.trim();
			if (resolved.length > 0) {
				return resolved;
			}
		}
	}

	return null;
}

function parseList(input) {
	if (!input) {
		return [];
	}

	return input
		.split(',')
		.map((item) => item.trim())
		.filter((item) => item.length > 0);
}

function buildTargetUrls() {
	const explicitUrls = parseList(process.env.LIGHTHOUSE_TARGET_URLS);
	if (explicitUrls.length > 0) {
		return explicitUrls;
	}

	const baseUrl = process.env.LIGHTHOUSE_BASE_URL?.trim() || DEFAULT_BASE_URL;
	const targetPaths = parseList(process.env.LIGHTHOUSE_TARGET_PATHS);
	const paths = targetPaths.length > 0 ? targetPaths : [DEFAULT_TARGET_PATH];

	return paths.map((targetPath) => new URL(targetPath, `${baseUrl.replace(/\/$/, '')}/`).toString());
}

function buildProfileArgs(profile) {
	if (profile === 'desktop') {
		return [
			'--preset=desktop',
			'--form-factor=desktop',
			'--throttling-method=simulate',
			'--throttling.rttMs=40',
			'--throttling.throughputKbps=10240',
			'--throttling.cpuSlowdownMultiplier=1',
			'--screenEmulation.mobile=false',
			'--screenEmulation.width=1350',
			'--screenEmulation.height=940'
		];
	}

	if (profile === 'mobile') {
		return [
			'--form-factor=mobile',
			'--screenEmulation.mobile=true',
			'--screenEmulation.width=390',
			'--screenEmulation.height=844',
			'--throttling-method=simulate',
			'--throttling.rttMs=150',
			'--throttling.throughputKbps=1638',
			'--throttling.cpuSlowdownMultiplier=4'
		];
	}

	throw new Error(`Unsupported Lighthouse profile: ${profile}`);
}

function createOutputPath(profile, index, totalTargets) {
	const outputDir = process.env.LIGHTHOUSE_OUTPUT_DIR?.trim() || DEFAULT_OUTPUT_DIR;
	if (totalTargets === 1) {
		return path.posix.join(outputDir, `latest-${profile}`);
	}
	return path.posix.join(outputDir, `latest-${profile}-${index + 1}`);
}

async function waitForTargetReady(url, timeoutMs) {
	const startedAt = Date.now();
	while (Date.now() - startedAt < timeoutMs) {
		try {
			const response = await fetch(url, { method: 'GET' });
			if (response.ok) {
				return;
			}
		} catch {
			// Le serveur n'est pas encore prêt.
		}
		await new Promise((resolve) => setTimeout(resolve, 400));
	}

	throw new Error(
		`Target URL not reachable within ${timeoutMs}ms: ${url}. ` +
			"Start the preview/backend first, or run 'npm run lighthouse:suite'."
	);
}

function runLighthouse(url, profile, index, totalTargets) {
	const outputPath = createOutputPath(profile, index, totalTargets);
	const profileArgs = buildProfileArgs(profile);
	const chromeFlags =
		process.env.LIGHTHOUSE_CHROME_FLAGS ||
		'--headless=new --no-sandbox --disable-extensions --disable-component-extensions-with-background-pages';
	const chromePath = process.env.LIGHTHOUSE_CHROME_PATH?.trim();

	const args = [
		url,
		...profileArgs,
		'--output=html',
		'--output=json',
		`--output-path=${outputPath}`,
		`--chrome-flags=${chromeFlags}`
	];

	const env = { ...process.env };
	if (chromePath) {
		env.CHROME_PATH = chromePath;
	} else if (!env.CHROME_PATH) {
		const detectedBrowser = findBrowserExecutable();
		if (detectedBrowser) {
			env.CHROME_PATH = detectedBrowser;
		}
	}

	return new Promise((resolve, reject) => {
		console.info(`[lighthouse] profile=${profile} target=${url}`);
		const child = spawn(LIGHTHOUSE_BINARY, args, {
			stdio: 'inherit',
			shell: false,
			env
		});

		child.on('error', reject);
		child.on('exit', (code) => {
			if (code === 0) {
				resolve();
				return;
			}
			reject(new Error(`Lighthouse failed for ${url} with code ${code}`));
		});
	});
}

async function main() {
	const profile = process.argv[2]?.trim();
	if (profile !== 'desktop' && profile !== 'mobile') {
		throw new Error('Usage: node ./scripts/run-lighthouse-profile.mjs <desktop|mobile>');
	}

	const targets = buildTargetUrls();
	const outputDir = process.env.LIGHTHOUSE_OUTPUT_DIR?.trim() || DEFAULT_OUTPUT_DIR;
	const readyTimeoutMs = Number.parseInt(
		process.env.LIGHTHOUSE_SERVER_READY_TIMEOUT_MS || `${DEFAULT_SERVER_READY_TIMEOUT_MS}`,
		10
	);
	await mkdir(outputDir, { recursive: true });
	for (let index = 0; index < targets.length; index += 1) {
		await waitForTargetReady(targets[index], readyTimeoutMs);
		await runLighthouse(targets[index], profile, index, targets.length);
	}
}

main().catch((error) => {
	console.error(error instanceof Error ? error.message : String(error));
	process.exit(1);
});
