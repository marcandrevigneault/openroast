import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import SessionControls from './SessionControls.svelte';

describe('SessionControls', () => {
	it('shows Monitor button when idle', () => {
		render(SessionControls, { props: { sessionState: 'idle' } });
		expect(screen.getByText(/Monitor/)).toBeInTheDocument();
	});

	it('shows Record and Stop when monitoring', () => {
		render(SessionControls, { props: { sessionState: 'monitoring' } });
		expect(screen.getByText(/Record/)).toBeInTheDocument();
		expect(screen.getByText(/Stop/)).toBeInTheDocument();
	});

	it('shows Stop Recording when recording', () => {
		render(SessionControls, { props: { sessionState: 'recording' } });
		expect(screen.getByText(/Stop Recording/)).toBeInTheDocument();
	});

	it('shows New Session when finished', () => {
		render(SessionControls, { props: { sessionState: 'finished' } });
		expect(screen.getByText(/New Session/)).toBeInTheDocument();
	});

	it('calls onstart when Monitor clicked', async () => {
		const onstart = vi.fn();
		render(SessionControls, { props: { sessionState: 'idle', onstart } });
		await fireEvent.click(screen.getByText(/Monitor/));
		expect(onstart).toHaveBeenCalledOnce();
	});

	it('calls onrecord when Record clicked', async () => {
		const onrecord = vi.fn();
		render(SessionControls, { props: { sessionState: 'monitoring', onrecord } });
		await fireEvent.click(screen.getByText(/Record/));
		expect(onrecord).toHaveBeenCalledOnce();
	});

	it('calls onstop when Stop clicked during monitoring', async () => {
		const onstop = vi.fn();
		render(SessionControls, { props: { sessionState: 'monitoring', onstop } });
		await fireEvent.click(screen.getByText(/^.*Stop$/));
		expect(onstop).toHaveBeenCalledOnce();
	});

	it('calls onstoprecord when Stop Recording clicked', async () => {
		const onstoprecord = vi.fn();
		render(SessionControls, { props: { sessionState: 'recording', onstoprecord } });
		await fireEvent.click(screen.getByText(/Stop Recording/));
		expect(onstoprecord).toHaveBeenCalledOnce();
	});
});
