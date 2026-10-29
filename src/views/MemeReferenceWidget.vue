<!--
  - SPDX-FileCopyrightText: 2026 meatybot
  - SPDX-License-Identifier: MIT
-->
<template>
	<div class="caption-obvious-reference">
		<div class="meme-wrapper">
			<div v-if="!isLoaded" class="loading-icon">
				<NcLoadingIcon :size="44" :name="t('caption_obvious', 'Loading meme')" />
			</div>
			<img v-show="isLoaded"
				class="image"
				:src="src"
				:alt="richObject.text || t('caption_obvious', 'imgflip meme')"
				@load="isLoaded = true">
			<a class="attribution"
				:href="richObject.page_url"
				target="_blank"
				rel="noopener noreferrer">
				imgflip.com
			</a>
		</div>
	</div>
</template>

<script>
import NcLoadingIcon from '@nextcloud/vue/components/NcLoadingIcon'
import { imageUrl } from '../exapp.js'

export default {
	name: 'MemeReferenceWidget',

	components: {
		NcLoadingIcon,
	},

	props: {
		richObjectType: {
			type: String,
			default: '',
		},
		richObject: {
			type: Object,
			default: null,
		},
		accessible: {
			type: Boolean,
			default: true,
		},
	},

	data() {
		return {
			isLoaded: false,
		}
	},

	computed: {
		// Through the ExApp: the Nextcloud CSP does not allow images from i.imgflip.com.
		src() {
			return imageUrl(this.richObject.slug, this.richObject.ext)
		},
	},
}
</script>

<style scoped lang="scss">
.caption-obvious-reference {
	width: 100%;
	padding: 12px;
	white-space: normal;
	box-sizing: border-box;

	.meme-wrapper {
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 4px;

		.image {
			max-height: 550px;
			max-width: 100%;
			border-radius: var(--border-radius-element);
		}

		.attribution {
			color: var(--color-text-maxcontrast);
			font-size: .9em;
		}
	}
}
</style>
