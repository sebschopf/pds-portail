import { spawn } from 'node:child_process';

const PREVIEW_URL = 'http://127.0.0.1:4173/';
const PREVIEW_TIMEOUT_MS = 30_000;

function runCommand(command, args, options = {}) {
	return new Promise((resolve, reject) => {
		const child = spawn(command, args, {
			stdio: 'inherit',
			shell: false,
			...options
		});

		child.on('error', reject);
		child.on('exit', (code) => {
			if (code === 0) {
				resolve(code);
				return;
			}
			reject(new Error(`${command} ${args.join(' ')} failed with code ${code}`));
		});
	});
}

async function waitForPreviewReady(url, timeoutMs) {
	const startedAt = Date.now();
	while (Date.now() - startedAt < timeoutMs) {
		try {
			const response = await fetch(url, { method: 'GET' });
			if (response.ok) {
				return;
			}
		} catch {
			// Preview is not ready yet.
		}
		await new Promise((resolve) => setTimeout(resolve, 400));
	}
	throw new Error(`Preview server did not become ready within ${timeoutMs}ms`);
}

async function main() {
	const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
	const preview = spawn(npmCmd, ['run', 'preview', '--', '--host', '127.0.0.1', '--port', '4173'], {
		stdio: 'inherit',
		shell: false
	});

	const stopPreview = () => {
		if (!preview.killed) {
			preview.kill('SIGTERM');
		}
	};

	process.on('SIGINT', () => {
		stopPreview();
		process.exit(130);
	});
	process.on('SIGTERM', () => {
		stopPreview();
		process.exit(143);
	});

	try {
		await waitForPreviewReady(PREVIEW_URL, PREVIEW_TIMEOUT_MS);
		await runCommand(npmCmd, ['run', 'lighthouse:all']);
	} finally {
		stopPreview();
	}
}

main().catch((error) => {
	console.error(error instanceof Error ? error.message : String(error));
	process.exit(1);
});
