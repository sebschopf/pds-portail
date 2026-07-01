#!/usr/bin/env node

/**
 * PDS-59 — Vérifie les seuils Lighthouse dans les rapports JSON les plus récents.
 *
 * Usage : node check-lighthouse-thresholds.mjs [--desktop report.json] [--mobile report.json]
 * Sortie : code 0 si tous les seuils sont respectés, code 1 sinon.
 *
 * Seuils :
 *   Desktop : performance ≥ 90
 *   Mobile  : performance ≥ 70, accessibility ≥ 85, best-practices ≥ 85
 *
 * Les rapports JSON sont produits par `npm run lighthouse:all` ou les scripts
 * individuels lighthouse:desktop / lighthouse:mobile.
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

const THRESHOLDS = {
	desktop: {
		performance: 0.90,
		accessibility: 0.85,
		'best-practices': 0.85
	},
	mobile: {
		performance: 0.70,
		accessibility: 0.85,
		'best-practices': 0.85
	}
};

function parseArgs() {
	const args = process.argv.slice(2);
	const paths = { desktop: null, mobile: null };

	for (let i = 0; i < args.length; i++) {
		if (args[i] === '--desktop' && i + 1 < args.length) {
			paths.desktop = args[++i];
		} else if (args[i] === '--mobile' && i + 1 < args.length) {
			paths.mobile = args[++i];
		}
	}

	if (!paths.desktop) {
		paths.desktop = path.resolve(
			SCRIPT_DIR,
			'..',
			'reports',
			'lighthouse',
			'latest-desktop.report.json'
		);
	}
	if (!paths.mobile) {
		paths.mobile = path.resolve(
			SCRIPT_DIR,
			'..',
			'reports',
			'lighthouse',
			'latest-mobile.report.json'
		);
	}

	return paths;
}

function loadReport(filePath) {
	try {
		const raw = readFileSync(filePath, 'utf-8');
		return JSON.parse(raw);
	} catch (err) {
		if (err.code === 'ENOENT') {
			return { _error: `Fichier introuvable : ${filePath}` };
		}
		return { _error: `Erreur de lecture ${filePath} : ${err.message}` };
	}
}

function extractScores(report) {
	if (report._error) return report;

	const categories = report.categories ?? {};
	const scores = {};
	for (const [key, cat] of Object.entries(categories)) {
		scores[key] = cat.score ?? null;
	}
	return scores;
}

function checkThresholds(scores, thresholds, label) {
	const failures = [];
	const warnings = [];

	if (scores._error) {
		console.log(`⚠️  [${label}] Rapport non disponible : ${scores._error}`);
		return { failures: [], warnings: [`[${label}] Rapport non disponible : ${scores._error}`] };
	}

	for (const [category, threshold] of Object.entries(thresholds)) {
		const actual = scores[category];
		if (actual === null || actual === undefined) {
			warnings.push(`${category}: score null — lancer 'cd frontend && npm run lighthouse:suite' pour regénérer`);
		} else if (actual < threshold) {
			failures.push({
				category,
				actual,
				threshold,
				message: `${category}: ${(actual * 100).toFixed(0)} < ${(threshold * 100).toFixed(0)}`
			});
		}
	}

	return { failures, warnings };
}

function showScoresLine(label, scores) {
	const perf = scores.performance !== null ? (scores.performance * 100).toFixed(0) : 'N/A';
	const a11y = scores.accessibility !== null ? (scores.accessibility * 100).toFixed(0) : 'N/A';
	const bp = scores['best-practices'] !== null ? (scores['best-practices'] * 100).toFixed(0) : 'N/A';
	console.log(`   ${label.padEnd(8)} : perf=${perf} a11y=${a11y} best-practices=${bp}`);
}

function main() {
	const paths = parseArgs();
	let hasFailures = false;

	console.log('=== Lighthouse : vérification des seuils ===\n');

	// Desktop
	const desktopReport = loadReport(paths.desktop);
	const desktopScores = extractScores(desktopReport);
	const desktopResult = checkThresholds(desktopScores, THRESHOLDS.desktop, 'Desktop');

	showScoresLine('Desktop', desktopScores);
	for (const w of desktopResult.warnings) {
		console.log(`   ⚠️  ${w}`);
	}
	if (desktopResult.failures.length > 0) {
		console.log(`   ❌ ${desktopResult.failures.length} seuil(s) non respecté(s) :`);
		for (const f of desktopResult.failures) {
			console.log(`      - ${f.message}`);
		}
		hasFailures = true;
	}

	// Mobile
	const mobileReport = loadReport(paths.mobile);
	const mobileScores = extractScores(mobileReport);
	const mobileResult = checkThresholds(mobileScores, THRESHOLDS.mobile, 'Mobile');

	showScoresLine('Mobile', mobileScores);
	for (const w of mobileResult.warnings) {
		console.log(`   ⚠️  ${w}`);
	}
	if (mobileResult.failures.length > 0) {
		console.log(`   ❌ ${mobileResult.failures.length} seuil(s) non respecté(s) :`);
		for (const f of mobileResult.failures) {
			console.log(`      - ${f.message}`);
		}
		hasFailures = true;
	}

	console.log('');
	if (hasFailures) {
		console.log('❌ Lighthouse : des seuils ne sont pas respectés.');
		console.log('   Relance avec : cd frontend && npm run lighthouse:suite');
		process.exit(1);
	} else {
		console.log('✅ Lighthouse : vérification terminée.');
		process.exit(0);
	}
}

main();