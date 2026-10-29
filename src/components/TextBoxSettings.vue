<!--
  - SPDX-FileCopyrightText: 2026 meatybot
  - SPDX-License-Identifier: MIT
-->
<template>
	<div class="text-box-settings" :class="{ selected }" @focusin="$emit('select')">
		<NcTextArea ref="text"
			:model-value="box.text"
			:label="t('caption_obvious', 'Text {number}', { number })"
			resize="vertical"
			rows="2"
			@update:model-value="update({ text: $event })" />
		<NcSelect :model-value="fontOptions.find((o) => o.id === box.font)"
			:options="fontOptions"
			:input-label="t('caption_obvious', 'Font')"
			:clearable="false"
			:loading="fontLoading"
			@update:model-value="update({ font: $event.id })" />
		<div class="row">
			<NcSelect :model-value="alignOptions.find((o) => o.id === box.align)"
				:options="alignOptions"
				:input-label="t('caption_obvious', 'Align')"
				:clearable="false"
				@update:model-value="update({ align: $event.id })" />
			<NcSelect :model-value="valignOptions.find((o) => o.id === box.valign)"
				:options="valignOptions"
				:input-label="t('caption_obvious', 'Position')"
				:clearable="false"
				@update:model-value="update({ valign: $event.id })" />
		</div>
		<div class="row colors">
			<NcColorPicker :model-value="box.color" advanced-fields @update:model-value="update({ color: $event })">
				<NcButton :aria-label="t('caption_obvious', 'Text colour')" variant="tertiary">
					<template #icon>
						<span class="swatch" :style="{ background: box.color }" />
					</template>
					{{ t('caption_obvious', 'Text') }}
				</NcButton>
			</NcColorPicker>
			<NcColorPicker :model-value="box.outline" advanced-fields @update:model-value="update({ outline: $event })">
				<NcButton :aria-label="t('caption_obvious', 'Outline colour')" variant="tertiary">
					<template #icon>
						<span class="swatch" :style="{ background: box.outline }" />
					</template>
					{{ t('caption_obvious', 'Outline') }}
				</NcButton>
			</NcColorPicker>
			<NcCheckboxRadioSwitch :model-value="box.caps" @update:model-value="update({ caps: $event })">
				{{ t('caption_obvious', 'All caps') }}
			</NcCheckboxRadioSwitch>
		</div>
	</div>
</template>

<script>
import NcButton from '@nextcloud/vue/components/NcButton'
import NcCheckboxRadioSwitch from '@nextcloud/vue/components/NcCheckboxRadioSwitch'
import NcColorPicker from '@nextcloud/vue/components/NcColorPicker'
import NcSelect from '@nextcloud/vue/components/NcSelect'
import NcTextArea from '@nextcloud/vue/components/NcTextArea'
import { FONTS } from '../fonts.js'

export default {
	name: 'TextBoxSettings',

	components: {
		NcButton,
		NcCheckboxRadioSwitch,
		NcColorPicker,
		NcSelect,
		NcTextArea,
	},

	props: {
		box: {
			type: Object,
			required: true,
		},
		number: {
			type: Number,
			required: true,
		},
		selected: {
			type: Boolean,
			default: false,
		},
		fontLoading: {
			type: Boolean,
			default: false,
		},
	},

	emits: ['update', 'select'],

	data() {
		return {
			// Font files download only when a box uses them, so the list shows plain names, not previews.
			fontOptions: FONTS.map(({ id, label }) => ({ id, label })),
			alignOptions: [
				{ id: 'left', label: t('caption_obvious', 'Left') },
				{ id: 'center', label: t('caption_obvious', 'Centre') },
				{ id: 'right', label: t('caption_obvious', 'Right') },
			],
			valignOptions: [
				{ id: 'top', label: t('caption_obvious', 'Top') },
				{ id: 'middle', label: t('caption_obvious', 'Middle') },
				{ id: 'bottom', label: t('caption_obvious', 'Bottom') },
			],
		}
	},

	methods: {
		update(changes) {
			this.$emit('update', changes)
		},

		focus() {
			this.$refs.text.focus()
		},
	},
}
</script>

<style scoped lang="scss">
.text-box-settings {
	border: 2px solid var(--color-border);
	border-radius: var(--border-radius-large);
	padding: 8px;
	margin-bottom: 8px;
	display: flex;
	flex-direction: column;
	gap: 6px;

	&.selected {
		border-color: var(--color-primary-element);
	}

	.row {
		display: flex;
		gap: 4px;

		> * {
			flex: 1;
			min-width: 0;
		}
	}

	.colors {
		align-items: center;
		flex-wrap: wrap;

		> * {
			flex: 0 0 auto;
		}
	}

	.swatch {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 1px solid var(--color-border-dark);
	}
}
</style>
