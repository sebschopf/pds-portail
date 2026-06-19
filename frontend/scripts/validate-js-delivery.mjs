import { readFile } from 'node:fs/promises';

const DEFAULT_DESKTOP_REPORT = './reports/lighthouse/latest-desktop.report.json';
const DEFAULT_MOBILE_REPORT = './reports/lighthouse/latest-mobile.report.json';

const BUDGETS = {
	desktop: {
		initialJsTransferBytes: 50 * 1024,
		alertThresholdRatio: 0.9,
		unusedSameOriginBytes: 8 * 1024
	},
	mobile: {
		initialJsTransferBytes: 50 * 1024,
		alertThresholdRatio: 0.9,
		unusedSameOriginBytes: 8 * 1024
	}
};

function toKiB(value) {
	return `${(value / 1024).toFixed(1)} KiB`;
}

async function readReport(reportPath) {
	const content = await readFile(reportPath, 'utf8');
	return JSON.parse(content);
}

function computeJsTransferBytes(report) {
	const origin = new URL(report.finalUrl).origin;
	const items = report.audits['network-requests']?.details?.items ?? [];
	return items
		.filter((item) => item.resourceType === 'Script' && item.url.startsWith(origin))
		.reduce((sum, item) => sum + (item.transferSize ?? 0), 0);
}

function computeUnusedSameOriginBytes(report) {
	const origin = new URL(report.finalUrl).origin;
	const items = report.audits['unused-javascript']?.details?.items ?? [];
	return items
		.filter((item) => typeof item.url === 'string' && item.url.startsWith(origin))
		.reduce((sum, item) => sum + (item.wastedBytes ?? 0), 0);
}

function assertUnminifiedJavascriptAudit(profile, report) {
	const score = report.audits['unminified-javascript']?.score;
	if (score !== 1) {
		throw new Error(
			`[${profile}] audit unminified-javascript attendu a 1. Valeur actuelle: ${String(score)}`
		);
	}
}

function checkBudget(profile, measuredBytes, budgetBytes, alertThresholdRatio) {
	if (measuredBytes > budgetBytes) {
		throw new Error(
			`[${profile}] budget JS depasse: ${toKiB(measuredBytes)} > ${toKiB(budgetBytes)}`
		);
	}

	if (measuredBytes > budgetBytes * alertThresholdRatio) {
		console.warn(
			`[${profile}] alerte budget: ${toKiB(measuredBytes)} proche du seuil ${toKiB(budgetBytes)} (ratio ${(alertThresholdRatio * 100).toFixed(0)}%)`
		);
	}
}

async function main() {
	const desktopReportPath = process.env.LIGHTHOUSE_DESKTOP_REPORT || DEFAULT_DESKTOP_REPORT;
	const mobileReportPath = process.env.LIGHTHOUSE_MOBILE_REPORT || DEFAULT_MOBILE_REPORT;

	const desktopReport = await readReport(desktopReportPath);
	const mobileReport = await readReport(mobileReportPath);

	for (const [profile, report] of [
		['desktop', desktopReport],
		['mobile', mobileReport]
	]) {
		const budget = BUDGETS[profile];
		assertUnminifiedJavascriptAudit(profile, report);

		const initialJsTransferBytes = computeJsTransferBytes(report);
		const unusedSameOriginBytes = computeUnusedSameOriginBytes(report);

		checkBudget(
			profile,
			initialJsTransferBytes,
			budget.initialJsTransferBytes,
			budget.alertThresholdRatio
		);
		checkBudget(
			profile,
			unusedSameOriginBytes,
			budget.unusedSameOriginBytes,
			budget.alertThresholdRatio
		);

		console.info(
			`[${profile}] minification=ok | js-transfer=${toKiB(initialJsTransferBytes)} | unused-same-origin=${toKiB(unusedSameOriginBytes)}`
		);
	}
}

main().catch((error) => {
	console.error(error instanceof Error ? error.message : String(error));
	process.exit(1);
});
