import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import EventButtons from './EventButtons.svelte';

describe('EventButtons', () => {
	it('renders all event buttons', () => {
		render(EventButtons, { props: {} });
		expect(screen.getByText('CHARGE')).toBeInTheDocument();
		expect(screen.getByText('DRY')).toBeInTheDocument();
		expect(screen.getByText('FCs')).toBeInTheDocument();
		expect(screen.getByText('FCe')).toBeInTheDocument();
		expect(screen.getByText('SCs')).toBeInTheDocument();
		expect(screen.getByText('DROP')).toBeInTheDocument();
		expect(screen.getByText('COOL')).toBeInTheDocument();
	});

	it('buttons are disabled when disabled prop is true', () => {
		render(EventButtons, { props: { disabled: true } });
		const buttons = screen.getAllByRole('button');
		buttons.forEach((btn) => {
			expect(btn).toBeDisabled();
		});
	});

	it('buttons are enabled when disabled prop is false', () => {
		render(EventButtons, { props: { disabled: false } });
		const buttons = screen.getAllByRole('button');
		buttons.forEach((btn) => {
			expect(btn).not.toBeDisabled();
		});
	});

	it('calls onmark with event type when clicked', async () => {
		const onmark = vi.fn();
		render(EventButtons, { props: { onmark } });
		await fireEvent.click(screen.getByText('CHARGE'));
		expect(onmark).toHaveBeenCalledWith('CHARGE');
	});

	it('disables already marked events', () => {
		const events = [
			{
				event_type: 'CHARGE' as const,
				timestamp_ms: 5000,
				auto_detected: false,
				bt_at_event: 155,
				et_at_event: 210
			}
		];
		render(EventButtons, { props: { events } });
		// CHARGE button should be disabled since it's already marked
		const chargeBtn = screen.getByText('CHARGE').closest('button');
		expect(chargeBtn).toBeDisabled();
		// Other buttons should still be enabled
		const dryBtn = screen.getByText('DRY').closest('button');
		expect(dryBtn).not.toBeDisabled();
	});

	it('shows timestamp for marked events', () => {
		const events = [
			{
				event_type: 'CHARGE' as const,
				timestamp_ms: 65000,
				auto_detected: false,
				bt_at_event: 155,
				et_at_event: 210
			}
		];
		render(EventButtons, { props: { events } });
		// Should show "1:05" (65 seconds = 1:05)
		expect(screen.getByText('1:05')).toBeInTheDocument();
	});
});
