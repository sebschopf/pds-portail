import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { parse } from 'culori';

const FRONTEND_SRC_PATH = resolve(process.cwd(), 'src');
const APP_CSS_PATH = resolve(FRONTEND_SRC_PATH, 'app.css');

/**
 * Résout récursivement les @import CSS pour collecter tout le contenu.
 * Supporte @import './lib/tokens/index.css' dans app.css.
 */
function resolveCssImports(filePath, visited = new Set()) {
	const absPath = resolve(filePath);
	if (visited.has(absPath)) return '';
	visited.add(absPath);

	const content = readFileSync(absPath, 'utf-8');
	const importRegex = /@import\s+['"]([^'"]+)['"]\s*;/g;

	let resolved = content;
	let match;
	while ((match = importRegex.exec(content)) !== null) {
		const importPath = resolve(filePath, '..', match[1]);
		const importedContent = resolveCssImports(importPath, visited);
		resolved = resolved.replace(match[0], importedContent);
	}

	return resolved;
}

const appCss = resolveCssImports(APP_CSS_PATH);

function collectSourceFiles(directoryPath, fileList = []) {
	for (const entry of readdirSync(directoryPath, { withFileTypes: true })) {
		const entryPath = resolve(directoryPath, entry.name);
		if (entry.isDirectory()) {
			if (entry.name === 'node_modules') {
				continue;
			}
			collectSourceFiles(entryPath, fileList);
			continue;
		}
		if (/\.(svelte|css|ts|js|mjs)$/i.test(entry.name)) {
			fileList.push(entryPath);
		}
	}
	return fileList;
}

function getLineNumberFromIndex(content, index) {
	return content.slice(0, index).split('\n').length;
}

function isAllowedFontSizeValue(rawValue) {
	const value = rawValue.trim().toLowerCase();
	return (
		value.includes('var(') ||
		value.includes('clamp(') ||
		value === 'inherit' ||
		value === 'initial' ||
		value === 'unset' ||
		value === 'revert' ||
		value === 'revert-layer'
	);
}

function isAllowedLineHeightValue(rawValue) {
	const value = rawValue.trim().toLowerCase();
	return (
		value.includes('var(') ||
		value === 'normal' ||
		value === 'inherit' ||
		value === 'initial' ||
		value === 'unset' ||
		value === 'revert' ||
		value === 'revert-layer'
	);
}

const forbiddenColorFormats = [/#[0-9a-fA-F]{3,8}/g, /\brgb\(/gi, /\brgba\(/gi, /\bhsl\(/gi, /\bhsla\(/gi];
for (const pattern of forbiddenColorFormats) {
	if (pattern.test(appCss)) {
		throw new Error(`Format couleur interdit detecte dans src/app.css: ${pattern}`);
	}
}

const tokenMatches = [...appCss.matchAll(/--([a-z0-9-]+)\s*:\s*([^;]+);/gi)];
const tokens = new Map(tokenMatches.map((match) => [match[1], match[2].trim()]));

const colorTokens = [...tokens.entries()].filter(([name]) => name.startsWith('color-'));
if (colorTokens.length === 0) {
	throw new Error('Aucun token --color-* detecte.');
}

if (!tokens.has('radius-none')) {
	throw new Error('Token obligatoire manquant: --radius-none');
}

if (tokens.has('radius-sm') || tokens.has('radius-md') || tokens.has('radius-lg') || tokens.has('radius-pill')) {
	throw new Error('Tokens de radius interdits detectes: seule la politique --radius-none est autorisee.');
}

for (const [name, value] of colorTokens) {
	if (!value.startsWith('oklch(')) {
		throw new Error(`Token ${name} doit etre en oklch(...), valeur actuelle: ${value}`);
	}
}

function relativeLuminance(rgbColor) {
	const channels = [rgbColor.r, rgbColor.g, rgbColor.b].map((channel) => {
		if (channel <= 0.03928) {
			return channel / 12.92;
		}
		return ((channel + 0.055) / 1.055) ** 2.4;
	});
	return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrastRatio(colorA, colorB) {
	const parsedA = parse(colorA);
	const parsedB = parse(colorB);
	if (!parsedA || !parsedB) {
		throw new Error(`Impossible de parser les couleurs: ${colorA} / ${colorB}`);
	}
	const lumA = relativeLuminance(parsedA);
	const lumB = relativeLuminance(parsedB);
	const [lighter, darker] = lumA >= lumB ? [lumA, lumB] : [lumB, lumA];
	return (lighter + 0.05) / (darker + 0.05);
}

function parseOklchToken(value) {
	const match = value.match(/^oklch\(\s*([0-9.]+%?)\s+([0-9.]+)\s+([0-9.]+)\s*\)$/i);
	if (!match) {
		throw new Error(`Valeur OKLCH invalide: ${value}`);
	}

	const lightness = match[1].endsWith('%')
		? Number.parseFloat(match[1]) / 100
		: Number.parseFloat(match[1]);
	const chroma = Number.parseFloat(match[2]);
	const hue = Number.parseFloat(match[3]);

	return { lightness, chroma, hue };
}

function hueDistance(hueA, hueB) {
	const delta = Math.abs(hueA - hueB) % 360;
	return Math.min(delta, 360 - delta);
}

function assertNear(actual, expected, tolerance, message) {
	if (Math.abs(actual - expected) > tolerance) {
		throw new Error(`${message}: attendu ${expected.toFixed(3)} ± ${tolerance.toFixed(3)}, obtenu ${actual.toFixed(3)}`);
	}
}

const requiredPairs = [
	['color-bg', 'color-on-bg'],
	['color-surface', 'color-on-surface'],
	['color-primary', 'color-on-primary'],
	['color-danger', 'color-on-danger'],
	['color-success', 'color-on-success'],
	['color-warning', 'color-on-warning']
];

for (const [bg, fg] of requiredPairs) {
	const bgColor = tokens.get(bg);
	const fgColor = tokens.get(fg);
	if (!bgColor || !fgColor) {
		throw new Error(`Couple de contraste manquant: --${bg} / --${fg}`);
	}
	const ratio = contrastRatio(bgColor, fgColor);
	if (ratio < 4.5) {
		throw new Error(
			`Contraste insuffisant pour --${bg} / --${fg}: ${ratio.toFixed(2)} (minimum AA: 4.5)`
		);
	}

	const bgToken = parseOklchToken(tokens.get('color-bg'));
	const surfaceToken = parseOklchToken(tokens.get('color-surface'));
	const borderToken = parseOklchToken(tokens.get('color-border'));
	const warningToken = parseOklchToken(tokens.get('color-warning'));
	const focusRingToken = parseOklchToken(tokens.get('color-focus-ring'));

	if (hueDistance(borderToken.hue, bgToken.hue) > 15) {
		throw new Error('color-border doit rester dans la famille de teinte du fond (hue proche).');
	}

	if (borderToken.chroma > 0.03) {
		throw new Error('color-border doit rester peu chromatique (<= 0.03).');
	}

	if (borderToken.lightness > bgToken.lightness - 0.08) {
		throw new Error('color-border doit etre plus sombre que color-bg d\u2019au moins 0.08 en lightness.');
	}

	if (hueDistance(surfaceToken.hue, bgToken.hue) > 10) {
		throw new Error('color-surface doit rester dans la famille de teinte du fond.');
	}

	if (surfaceToken.lightness < bgToken.lightness - 0.03) {
		throw new Error('color-surface doit rester tres proche de color-bg en lightness.');
	}

	assertNear(focusRingToken.hue, warningToken.hue, 2, 'color-focus-ring doit conserver la teinte de color-warning');
	assertNear(
		focusRingToken.lightness,
		warningToken.lightness - 0.08,
		0.03,
		'color-focus-ring doit deriver sa lightness depuis color-warning'
	);
	if (Math.abs(focusRingToken.chroma - warningToken.chroma) > 0.05) {
		throw new Error('color-focus-ring doit rester proche de color-warning en chroma.');
	}
}

const frontendFiles = collectSourceFiles(FRONTEND_SRC_PATH);
const hardcodedRadiusMatches = [];
const hardcodedFontSizeMatches = [];
const hardcodedLineHeightMatches = [];
const invalidBreakpointMatches = [];
const allowedMaxWidthBreakpoints = new Set(['40rem', '43.75rem']);
for (const filePath of frontendFiles) {
	if (filePath === APP_CSS_PATH) {
		continue;
	}
	const fileContent = readFileSync(filePath, 'utf-8');
	const fileRadiusMatches = [...fileContent.matchAll(/border-radius\s*:\s*([^;]+);/gi)].filter(
		(match) => !match[1].includes('var(--radius-none)')
	);
	if (fileRadiusMatches.length > 0) {
		hardcodedRadiusMatches.push({ filePath, count: fileRadiusMatches.length });
	}

	for (const match of fileContent.matchAll(/font-size\s*:\s*([^;]+);/gi)) {
		const value = match[1].trim();
		if (!isAllowedFontSizeValue(value)) {
			hardcodedFontSizeMatches.push({
				filePath,
				line: getLineNumberFromIndex(fileContent, match.index),
				value
			});
		}
	}

	for (const match of fileContent.matchAll(/line-height\s*:\s*([^;]+);/gi)) {
		const value = match[1].trim();
		if (!isAllowedLineHeightValue(value)) {
			hardcodedLineHeightMatches.push({
				filePath,
				line: getLineNumberFromIndex(fileContent, match.index),
				value
			});
		}
	}

	for (const match of fileContent.matchAll(/@media\s*\(\s*max-width\s*:\s*([^)]+)\)/gi)) {
		const value = match[1].trim().toLowerCase();
		if (!allowedMaxWidthBreakpoints.has(value)) {
			invalidBreakpointMatches.push({
				filePath,
				line: getLineNumberFromIndex(fileContent, match.index),
				value
			});
		}
	}
}

if (hardcodedRadiusMatches.length > 0) {
	const details = hardcodedRadiusMatches
		.map((entry) => `${entry.filePath.replace(process.cwd() + '/', '')} (${entry.count})`)
		.join(', ');
	throw new Error(`border-radius hardcode detecte hors token: ${details}`);
}

if (hardcodedFontSizeMatches.length > 0) {
	const details = hardcodedFontSizeMatches
		.map((entry) => `${entry.filePath.replace(process.cwd() + '/', '')}:${entry.line} (${entry.value})`)
		.join(', ');
	throw new Error(`font-size hardcode detecte hors token/clamp: ${details}`);
}

if (hardcodedLineHeightMatches.length > 0) {
	const details = hardcodedLineHeightMatches
		.map((entry) => `${entry.filePath.replace(process.cwd() + '/', '')}:${entry.line} (${entry.value})`)
		.join(', ');
	throw new Error(`line-height hardcode detecte hors token: ${details}`);
}

if (invalidBreakpointMatches.length > 0) {
	const details = invalidBreakpointMatches
		.map((entry) => `${entry.filePath.replace(process.cwd() + '/', '')}:${entry.line} (${entry.value})`)
		.join(', ');
	throw new Error(
		`Breakpoint max-width hors convention (autorises: 40rem, 43.75rem): ${details}`
	);
}

console.log('Design tokens valides: format OKLCH, contraste AA et conventions typographiques/responsive conformes.');
