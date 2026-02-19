<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { MachineState } from '$lib/stores/machine';
	import { createInitialState, processMessage } from '$lib/stores/machine';
	import type { RoastEventType, ServerMessage } from '$lib/types/ws-messages';
	import { generateDemoPoints } from '$lib/stores/demo';
	import MachinePanel from '$lib/components/MachinePanel.svelte';

	// Demo machine state
	let machine = $state<MachineState>({
		...createInitialState('demo-1', 'Stratto Pro 300'),
		driverState: 'connected',
		sessionState: 'monitoring'
	});

	// Pre-generated demo points, fed one at a time
	const demoPoints = generateDemoPoints(600);
	let demoIndex = $state(0);
	let timer: ReturnType<typeof setInterval> | undefined;

	function startDemo() {
		if (timer) return;
		demoIndex = 0;
		machine = {
			...machine,
			sessionState: 'monitoring',
			driverState: 'connected',
			history: [],
			events: [],
			currentTemp: null,
			error: null
		};
		timer = setInterval(() => {
			if (demoIndex >= demoPoints.length) {
				stopDemo();
				return;
			}
			const point = demoPoints[demoIndex];
			machine = processMessage(machine, {
				type: 'temperature',
				timestamp_ms: point.timestamp_ms,
				et: point.et,
				bt: point.bt,
				et_ror: point.et_ror,
				bt_ror: point.bt_ror,
				extra_channels: {}
			});
			demoIndex++;
		}, 100); // 10x speed for demo
	}

	function stopDemo() {
		if (timer) {
			clearInterval(timer);
			timer = undefined;
		}
		machine = processMessage(machine, {
			type: 'state',
			state: 'finished',
			previous_state: machine.sessionState
		});
	}

	function handleStart() {
		startDemo();
	}

	function handleStop() {
		stopDemo();
	}

	function handleRecord() {
		machine = processMessage(machine, {
			type: 'state',
			state: 'recording',
			previous_state: 'monitoring'
		});
	}

	function handleStopRecord() {
		stopDemo();
	}

	function handleMark(eventType: RoastEventType) {
		const lastPoint = machine.currentTemp;
		if (!lastPoint) return;
		machine = processMessage(machine, {
			type: 'event',
			event_type: eventType,
			timestamp_ms: lastPoint.timestamp_ms,
			auto_detected: false,
			bt_at_event: lastPoint.bt,
			et_at_event: lastPoint.et
		});
	}

	function handleControl(channel: string, value: number) {
		// In real mode, would send WebSocket control command
		console.log(`Control: ${channel} = ${value}`);
	}

	onMount(() => {
		startDemo();
	});

	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

<div class="dashboard">
	<MachinePanel
		{machine}
		onstart={handleStart}
		onstop={handleStop}
		onrecord={handleRecord}
		onstoprecord={handleStopRecord}
		onmark={handleMark}
		oncontrol={handleControl}
	/>
</div>

<style>
	.dashboard {
		max-width: 1100px;
		margin: 0 auto;
	}
</style>
