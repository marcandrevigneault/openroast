import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TemperatureDisplay from './TemperatureDisplay.svelte';

describe('TemperatureDisplay', () => {
	it('renders label', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 210.5, ror: 8.2 } });
		expect(screen.getByText('ET')).toBeInTheDocument();
	});

	it('renders temperature value with one decimal', () => {
		render(TemperatureDisplay, { props: { label: 'BT', value: 185.33, ror: 12.0 } });
		expect(screen.getByText('185.3')).toBeInTheDocument();
	});

	it('shows --- when value is null', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: null, ror: null } });
		expect(screen.getByText('---')).toBeInTheDocument();
	});

	it('shows positive RoR with + prefix', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 200, ror: 5.3 } });
		expect(screen.getByText('+5.3 /min')).toBeInTheDocument();
	});

	it('shows negative RoR without + prefix', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 200, ror: -2.1 } });
		expect(screen.getByText('-2.1 /min')).toBeInTheDocument();
	});

	it('shows default unit', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 200, ror: 5 } });
		expect(screen.getByText('°C')).toBeInTheDocument();
	});

	it('shows custom unit', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 392, ror: 9, unit: '°F' } });
		expect(screen.getByText('°F')).toBeInTheDocument();
	});

	it('shows --- for RoR when null', () => {
		render(TemperatureDisplay, { props: { label: 'ET', value: 200, ror: null } });
		expect(screen.getByText('--- /min')).toBeInTheDocument();
	});
});
