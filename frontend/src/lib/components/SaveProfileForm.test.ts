import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import SaveProfileForm from './SaveProfileForm.svelte';

describe('SaveProfileForm', () => {
	it('renders form fields', () => {
		render(SaveProfileForm, { props: { onsave: () => {} } });
		expect(screen.getByText('Save Profile', { selector: 'h4' })).toBeInTheDocument();
		expect(screen.getByPlaceholderText('e.g. Ethiopian Light')).toBeInTheDocument();
		expect(screen.getByPlaceholderText('e.g. Yirgacheffe')).toBeInTheDocument();
	});

	it('disables save button when name is empty', () => {
		render(SaveProfileForm, { props: { onsave: () => {} } });
		const btn = screen.getByRole('button', { name: 'Save Profile' });
		expect(btn).toBeDisabled();
	});

	it('enables save button when name is entered', async () => {
		render(SaveProfileForm, { props: { onsave: () => {} } });
		const input = screen.getByPlaceholderText('e.g. Ethiopian Light');
		await fireEvent.input(input, { target: { value: 'My Roast' } });
		const btn = screen.getByRole('button', { name: 'Save Profile' });
		expect(btn).not.toBeDisabled();
	});

	it('calls onsave with form data on submit', async () => {
		const onsave = vi.fn();
		render(SaveProfileForm, { props: { onsave } });

		const nameInput = screen.getByPlaceholderText('e.g. Ethiopian Light');
		const beanInput = screen.getByPlaceholderText('e.g. Yirgacheffe');

		await fireEvent.input(nameInput, { target: { value: '  My Roast  ' } });
		await fireEvent.input(beanInput, { target: { value: 'Ethiopian' } });
		const btn = screen.getByRole('button', { name: 'Save Profile' });
		await fireEvent.submit(btn.closest('form')!);

		expect(onsave).toHaveBeenCalledWith({
			name: 'My Roast',
			beanName: 'Ethiopian',
			beanWeight: 0
		});
	});

	it('shows saving state', () => {
		render(SaveProfileForm, { props: { onsave: () => {}, saving: true } });
		expect(screen.getByText('Saving…')).toBeInTheDocument();
	});

	it('shows saved message when saved', () => {
		render(SaveProfileForm, { props: { onsave: () => {}, saved: true } });
		expect(screen.getByText('Profile saved successfully.')).toBeInTheDocument();
	});
});
