import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import ControlSlider from './ControlSlider.svelte';

describe('ControlSlider', () => {
	it('renders label', () => {
		render(ControlSlider, { props: { label: 'Burner', value: 50 } });
		expect(screen.getByText('Burner')).toBeInTheDocument();
	});

	it('shows current value', () => {
		render(ControlSlider, { props: { label: 'Burner', value: 75 } });
		expect(screen.getByText('75')).toBeInTheDocument();
	});

	it('renders range input with correct attributes', () => {
		render(ControlSlider, {
			props: { label: 'Air', value: 50, min: 0, max: 100, step: 5 }
		});
		const input = screen.getByRole('slider');
		expect(input).toHaveAttribute('min', '0');
		expect(input).toHaveAttribute('max', '100');
		expect(input).toHaveAttribute('step', '5');
	});

	it('is disabled when disabled prop is true', () => {
		render(ControlSlider, {
			props: { label: 'Burner', value: 50, disabled: true }
		});
		const input = screen.getByRole('slider');
		expect(input).toBeDisabled();
	});

	it('calls onchange when slider moves', async () => {
		const onchange = vi.fn();
		render(ControlSlider, {
			props: { label: 'Burner', value: 50, onchange }
		});
		const input = screen.getByRole('slider');
		await fireEvent.input(input, { target: { value: '75' } });
		expect(onchange).toHaveBeenCalledWith(75);
	});
});
