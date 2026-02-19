<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { MachineState } from '$lib/stores/machine';
	import { createInitialState, processMessage } from '$lib/stores/machine';
	import type { RoastEventType } from '$lib/types/ws-messages';
	import { generateDemoPoints } from '$lib/stores/demo';
	import {
		createDashboardState,
		addMachine,
		removeMachine,
		updateLayout,
		generateMachineId,
		type DashboardState,
		type LayoutConfig
	} from '$lib/stores/dashboard';
	import MachinePanel from '$lib/components/MachinePanel.svelte';
	import DashboardToolbar from '$lib/components/DashboardToolbar.svelte';
	import AddMachineDialog from '$lib/components/AddMachineDialog.svelte';

	let dashboard = $state<DashboardState>(createDashboardState());
	let machineStates = $state<Map<string, MachineState>>(new Map());
	let timers = new Map<string, ReturnType<typeof setInterval>>();
	let demoData = new Map<string, { points: ReturnType<typeof generateDemoPoints>; index: number }>();

	let showAddDialog = $state(false);

	let gridStyle = $derived.by(() => {
		const { mode, columns } = dashboard.layout;
		if (mode === 'grid') return `grid-template-columns: repeat(${columns}, 1fr)`;
		if (mode === 'horizontal') return 'grid-template-columns: repeat(auto-fit, minmax(500px, 1fr))';
		return 'grid-template-columns: 1fr';
	});

	function startDemoForMachine(id: string) {
		const points = generateDemoPoints(600);
		demoData.set(id, { points, index: 0 });

		const state = machineStates.get(id);
		if (!state) return;

		machineStates.set(id, {
			...state,
			sessionState: 'monitoring',
			driverState: 'connected',
			history: [],
			events: [],
			currentTemp: null,
			error: null
		});
		machineStates = new Map(machineStates);

		const timer = setInterval(() => {
			const demo = demoData.get(id);
			const current = machineStates.get(id);
			if (!demo || !current) return;

			if (demo.index >= demo.points.length) {
				stopDemoForMachine(id);
				return;
			}

			const point = demo.points[demo.index];
			const updated = processMessage(current, {
				type: 'temperature',
				timestamp_ms: point.timestamp_ms,
				et: point.et,
				bt: point.bt,
				et_ror: point.et_ror,
				bt_ror: point.bt_ror,
				extra_channels: {}
			});
			demo.index++;
			machineStates.set(id, updated);
			machineStates = new Map(machineStates);
		}, 100);

		timers.set(id, timer);
	}

	function stopDemoForMachine(id: string) {
		const timer = timers.get(id);
		if (timer) {
			clearInterval(timer);
			timers.delete(id);
		}
		const current = machineStates.get(id);
		if (current) {
			machineStates.set(
				id,
				processMessage(current, {
					type: 'state',
					state: 'finished',
					previous_state: current.sessionState
				})
			);
			machineStates = new Map(machineStates);
		}
	}

	function handleAddMachine(name: string) {
		const id = generateMachineId();
		dashboard = addMachine(dashboard, { id, name });
		machineStates.set(id, createInitialState(id, name));
		machineStates = new Map(machineStates);
		startDemoForMachine(id);
	}

	function handleRemoveMachine(id: string) {
		stopDemoForMachine(id);
		demoData.delete(id);
		machineStates.delete(id);
		machineStates = new Map(machineStates);
		dashboard = removeMachine(dashboard, id);
	}

	function handleLayoutChange(layout: Partial<LayoutConfig>) {
		dashboard = updateLayout(dashboard, layout);
	}

	function handleStart(id: string) {
		startDemoForMachine(id);
	}

	function handleStop(id: string) {
		stopDemoForMachine(id);
	}

	function handleRecord(id: string) {
		const current = machineStates.get(id);
		if (!current) return;
		machineStates.set(
			id,
			processMessage(current, {
				type: 'state',
				state: 'recording',
				previous_state: 'monitoring'
			})
		);
		machineStates = new Map(machineStates);
	}

	function handleStopRecord(id: string) {
		stopDemoForMachine(id);
	}

	function handleMark(id: string, eventType: RoastEventType) {
		const current = machineStates.get(id);
		if (!current?.currentTemp) return;
		const lastPoint = current.currentTemp;
		machineStates.set(
			id,
			processMessage(current, {
				type: 'event',
				event_type: eventType,
				timestamp_ms: lastPoint.timestamp_ms,
				auto_detected: false,
				bt_at_event: lastPoint.bt,
				et_at_event: lastPoint.et
			})
		);
		machineStates = new Map(machineStates);
	}

	function handleControl(id: string, channel: string, value: number) {
		console.log(`Machine ${id} — Control: ${channel} = ${value}`);
	}

	onMount(() => {
		// Start with one demo machine
		handleAddMachine('Stratto Pro 300');
	});

	onDestroy(() => {
		for (const timer of timers.values()) {
			clearInterval(timer);
		}
	});
</script>

<div class="dashboard">
	<DashboardToolbar
		layout={dashboard.layout}
		machineCount={dashboard.machines.length}
		onaddmachine={() => (showAddDialog = true)}
		onlayoutchange={handleLayoutChange}
	/>

	<div class="machine-grid" style={gridStyle}>
		{#each dashboard.machines as m (m.id)}
			{@const state = machineStates.get(m.id)}
			{#if state}
				<MachinePanel
					machine={state}
					onstart={() => handleStart(m.id)}
					onstop={() => handleStop(m.id)}
					onrecord={() => handleRecord(m.id)}
					onstoprecord={() => handleStopRecord(m.id)}
					onmark={(eventType) => handleMark(m.id, eventType)}
					oncontrol={(channel, value) => handleControl(m.id, channel, value)}
					onremove={() => handleRemoveMachine(m.id)}
				/>
			{/if}
		{/each}
	</div>

	{#if dashboard.machines.length === 0}
		<div class="empty-state">
			<p>No machines added yet.</p>
			<button class="btn-start" onclick={() => (showAddDialog = true)}>+ Add Your First Machine</button>
		</div>
	{/if}

	<AddMachineDialog
		open={showAddDialog}
		onadd={handleAddMachine}
		onclose={() => (showAddDialog = false)}
	/>
</div>

<style>
	.dashboard {
		max-width: 1600px;
		margin: 0 auto;
	}

	.machine-grid {
		display: grid;
		gap: 16px;
	}

	.empty-state {
		text-align: center;
		padding: 80px 20px;
		color: #666;
	}

	.empty-state p {
		font-size: 1rem;
		margin-bottom: 16px;
	}

	.btn-start {
		background: #2e7d32;
		color: white;
		border: none;
		border-radius: 8px;
		padding: 10px 24px;
		font-size: 0.9rem;
		font-weight: 600;
		cursor: pointer;
	}

	.btn-start:hover {
		background: #388e3c;
	}
</style>
