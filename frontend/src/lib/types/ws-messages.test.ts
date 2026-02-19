import { describe, it, expect } from 'vitest';
import type {
	ServerMessage,
	ClientMessage,
	TemperatureMessage,
	EventMessage,
	StateMessage,
	ControlCommand,
	SessionCommand,
	ReplayControlCommand
} from './ws-messages';

describe('ServerMessage type discrimination', () => {
	it('narrows temperature message', () => {
		const msg: ServerMessage = {
			type: 'temperature',
			timestamp_ms: 3000,
			et: 210.5,
			bt: 185.3,
			et_ror: 8.2,
			bt_ror: 12.4,
			extra_channels: {}
		};

		if (msg.type === 'temperature') {
			// TypeScript narrows to TemperatureMessage
			expect(msg.et).toBe(210.5);
			expect(msg.bt_ror).toBe(12.4);
		}
	});

	it('narrows event message', () => {
		const msg: ServerMessage = {
			type: 'event',
			event_type: 'CHARGE',
			timestamp_ms: 5000,
			auto_detected: true,
			bt_at_event: 155.2,
			et_at_event: 210.5
		};

		if (msg.type === 'event') {
			expect(msg.event_type).toBe('CHARGE');
			expect(msg.auto_detected).toBe(true);
		}
	});

	it('narrows state message', () => {
		const msg: ServerMessage = {
			type: 'state',
			state: 'recording',
			previous_state: 'monitoring'
		};

		if (msg.type === 'state') {
			expect(msg.state).toBe('recording');
		}
	});

	it('handles all server message types', () => {
		const types: ServerMessage['type'][] = [
			'temperature',
			'event',
			'state',
			'alarm',
			'replay',
			'control_ack',
			'error',
			'connection'
		];
		expect(types).toHaveLength(8);
	});
});

describe('ClientMessage types', () => {
	it('creates control command', () => {
		const msg: ControlCommand = {
			type: 'control',
			channel: 'burner',
			value: 0.8
		};
		expect(msg.value).toBeGreaterThanOrEqual(0);
		expect(msg.value).toBeLessThanOrEqual(1);
	});

	it('creates session command', () => {
		const msg: SessionCommand = {
			type: 'command',
			action: 'start_recording'
		};
		expect(msg.action).toBe('start_recording');
	});

	it('creates mark event command', () => {
		const msg: SessionCommand = {
			type: 'command',
			action: 'mark_event',
			event_type: 'FCs'
		};
		expect(msg.event_type).toBe('FCs');
	});

	it('creates replay control', () => {
		const msg: ReplayControlCommand = {
			type: 'replay_control',
			action: 'start',
			profile_id: 'abc-123',
			speed: 2.0
		};
		expect(msg.speed).toBe(2.0);
	});

	it('creates sync command', () => {
		const msg: SessionCommand = {
			type: 'command',
			action: 'sync',
			last_timestamp_ms: 45000
		};
		expect(msg.last_timestamp_ms).toBe(45000);
	});
});

describe('Message dispatch pattern', () => {
	it('dispatches server messages by type', () => {
		const messages: ServerMessage[] = [
			{
				type: 'temperature',
				timestamp_ms: 0,
				et: 210,
				bt: 155,
				et_ror: 0,
				bt_ror: 0,
				extra_channels: {}
			},
			{
				type: 'event',
				event_type: 'CHARGE',
				timestamp_ms: 5000,
				auto_detected: true,
				bt_at_event: 155,
				et_at_event: 210
			},
			{
				type: 'error',
				code: 'DRIVER_READ_FAILED',
				message: 'timeout',
				recoverable: true
			}
		];

		const handled: string[] = [];
		for (const msg of messages) {
			switch (msg.type) {
				case 'temperature':
					handled.push('temp');
					break;
				case 'event':
					handled.push('event');
					break;
				case 'error':
					handled.push('error');
					break;
				default:
					handled.push('unknown');
			}
		}

		expect(handled).toEqual(['temp', 'event', 'error']);
	});
});
