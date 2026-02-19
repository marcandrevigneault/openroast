<script lang="ts">
	import type { MachineState } from '$lib/stores/machine';
	import type { SessionState, DriverState, RoastEventType } from '$lib/types/ws-messages';
	import TemperatureDisplay from './TemperatureDisplay.svelte';
	import RoastChart from './RoastChart.svelte';
	import ControlSlider from './ControlSlider.svelte';
	import EventButtons from './EventButtons.svelte';
	import SessionControls from './SessionControls.svelte';
	import ConnectionStatus from './ConnectionStatus.svelte';
	import SaveProfileForm from './SaveProfileForm.svelte';

	interface Props {
		machine: MachineState;
		onstart?: () => void;
		onstop?: () => void;
		onrecord?: () => void;
		onstoprecord?: () => void;
		onmark?: (eventType: RoastEventType) => void;
		oncontrol?: (channel: string, value: number) => void;
		onsave?: (data: { name: string; beanName: string; beanWeight: number }) => void;
	}

	let { machine, onstart, onstop, onrecord, onstoprecord, onmark, oncontrol, onsave }: Props =
		$props();

	let burner = $state(0);
	let airflow = $state(50);
	let drum = $state(60);
	let saving = $state(false);
	let saved = $state(false);

	let isRecording = $derived(machine.sessionState === 'recording');
	let isActive = $derived(machine.sessionState !== 'idle' && machine.sessionState !== 'finished');
	let showSaveForm = $derived(
		machine.sessionState === 'finished' && machine.history.length > 0 && !saved
	);

	function handleSave(data: { name: string; beanName: string; beanWeight: number }) {
		saving = true;
		onsave?.(data);
		saving = false;
		saved = true;
	}
</script>

<div class="machine-panel">
	<div class="panel-header">
		<h2 class="machine-name">{machine.machineName}</h2>
		<ConnectionStatus driverState={machine.driverState} sessionState={machine.sessionState} />
	</div>

	<div class="panel-body">
		<div class="left-column">
			<div class="temp-row">
				<TemperatureDisplay
					label="ET"
					value={machine.currentTemp?.et ?? null}
					ror={machine.currentTemp?.et_ror ?? null}
					color="#ff7043"
				/>
				<TemperatureDisplay
					label="BT"
					value={machine.currentTemp?.bt ?? null}
					ror={machine.currentTemp?.bt_ror ?? null}
					color="#42a5f5"
				/>
			</div>

			<RoastChart history={machine.history} />

			<div class="controls-row">
				<SessionControls
					sessionState={machine.sessionState}
					{onstart}
					{onstop}
					{onrecord}
					{onstoprecord}
				/>
				<EventButtons
					disabled={!isRecording}
					events={machine.events}
					{onmark}
				/>
			</div>
		</div>

		<div class="right-column">
			<div class="sliders">
				<ControlSlider
					label="Burner"
					bind:value={burner}
					min={0}
					max={100}
					step={5}
					color="#ff7043"
					disabled={!isActive}
					onchange={(v) => oncontrol?.('burner', v)}
				/>
				<ControlSlider
					label="Airflow"
					bind:value={airflow}
					min={0}
					max={100}
					step={5}
					color="#4fc3f7"
					disabled={!isActive}
					onchange={(v) => oncontrol?.('airflow', v)}
				/>
				<ControlSlider
					label="Drum"
					bind:value={drum}
					min={0}
					max={100}
					step={5}
					color="#81c784"
					disabled={!isActive}
					onchange={(v) => oncontrol?.('drum', v)}
				/>
			</div>

			{#if machine.error}
				<div class="error-banner">
					{machine.error}
				</div>
			{/if}

			{#if showSaveForm}
				<SaveProfileForm onsave={handleSave} {saving} {saved} />
			{/if}
		</div>
	</div>
</div>

<style>
	.machine-panel {
		background: #12122a;
		border: 1px solid #2a2a4a;
		border-radius: 12px;
		padding: 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.machine-name {
		font-size: 1rem;
		font-weight: 600;
		color: #e0e0e0;
		margin: 0;
	}

	.panel-body {
		display: flex;
		gap: 16px;
	}

	.left-column {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-width: 0;
	}

	.temp-row {
		display: flex;
		gap: 12px;
	}

	.controls-row {
		display: flex;
		gap: 12px;
		align-items: flex-start;
		flex-wrap: wrap;
	}

	.right-column {
		width: 200px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.sliders {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.error-banner {
		background: #3e1111;
		border: 1px solid #f44336;
		border-radius: 6px;
		padding: 8px 12px;
		color: #ff8a80;
		font-size: 0.8rem;
	}
</style>
