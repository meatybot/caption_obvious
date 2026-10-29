<!--
  - SPDX-FileCopyrightText: 2026 meatybot
  - SPDX-License-Identifier: MIT
-->
<template>
	<div class="caption-obvious-picker">
		<h2>{{ t('caption_obvious', 'imgflip meme') }}</h2>
		<div class="layout">
			<aside class="templates">
				<NcTextField ref="search"
					v-model="query"
					:label="t('caption_obvious', 'Search templates')"
					:show-trailing-button="query !== ''"
					trailing-button-icon="close"
					@trailing-button-click="query = ''"
					@update:model-value="onQueryChange">
					<template #icon>
						<MagnifyIcon :size="16" />
					</template>
				</NcTextField>
				<NcEmptyContent v-if="searching && templates.length === 0" :name="t('caption_obvious', 'Searching…')">
					<template #icon>
						<NcLoadingIcon />
					</template>
				</NcEmptyContent>
				<NcEmptyContent v-else-if="searchError" :name="searchError">
					<template #icon>
						<AlertCircleIcon />
					</template>
				</NcEmptyContent>
				<NcEmptyContent v-else-if="templates.length === 0" :name="t('caption_obvious', 'No templates found')">
					<template #icon>
						<ImageOffIcon />
					</template>
				</NcEmptyContent>
				<ul v-else class="results">
					<NcListItem v-for="item in templates"
						:key="item.id"
						:name="item.name"
						:active="template?.id === item.id"
						compact
						@click="openTemplate(item)">
						<template #icon>
							<img class="thumbnail"
								:src="templateImageUrl(item)"
								alt=""
								loading="lazy">
						</template>
						<template #subname>
							{{ n('caption_obvious', '%n text box', '%n text boxes', item.box_count) }}
						</template>
					</NcListItem>
				</ul>
			</aside>

			<section ref="stageArea" class="stage">
				<NcEmptyContent v-if="!template && !loadingTemplate" :name="t('caption_obvious', 'Pick a template')">
					<template #icon>
						<ImageIcon />
					</template>
				</NcEmptyContent>
				<NcLoadingIcon v-else-if="loadingTemplate" :size="44" />
				<MemeCanvas v-else
					:key="template.id"
					ref="canvas"
					:image="image"
					:template="template"
					:boxes="boxes"
					:selected-id="selectedId"
					:max-width="stageSize.width"
					:max-height="stageSize.height"
					@select="selectedId = $event"
					@update:box="updateBox($event.id, $event)"
					@font-loaded="onFontSettled($event)"
					@font-error="onFontSettled($event, true)" />
			</section>

			<aside class="settings">
				<template v-if="template">
					<TextBoxSettings v-for="(box, i) in boxes"
						:key="box.id"
						:ref="`box-${box.id}`"
						:box="box"
						:number="i + 1"
						:selected="box.id === selectedId"
						:font-loading="loadingFonts.includes(box.font)"
						@select="selectedId = box.id"
						@update="onBoxSettings(box.id, $event)" />
					<div class="actions">
						<NcButton wide @click="addBox">
							<template #icon>
								<PlusIcon :size="20" />
							</template>
							{{ t('caption_obvious', 'Add text box') }}
						</NcButton>
						<NcButton wide :disabled="selectedId === null" @click="deleteSelectedBox">
							<template #icon>
								<DeleteIcon :size="20" />
							</template>
							{{ t('caption_obvious', 'Delete selected box') }}
						</NcButton>
						<NcNoteCard v-if="fontError" type="warning">
							<p>{{ fontError }}</p>
							<NcButton variant="secondary" @click="retryFailedFonts">
								{{ t('caption_obvious', 'Retry') }}
							</NcButton>
						</NcNoteCard>
						<NcNoteCard v-if="hostError" type="error" :text="hostError" />
						<NcButton variant="primary"
							wide
							:disabled="hosting || !hasText"
							@click="insert">
							<template #icon>
								<NcLoadingIcon v-if="hosting" :size="20" />
								<CheckIcon v-else :size="20" />
							</template>
							{{ t('caption_obvious', 'Insert meme') }}
						</NcButton>
						<p class="hint">
							{{ t('caption_obvious', 'The meme is hosted publicly on imgflip.') }}
						</p>
					</div>
				</template>
			</aside>
		</div>
	</div>
</template>

<script>
import NcButton from '@nextcloud/vue/components/NcButton'
import NcEmptyContent from '@nextcloud/vue/components/NcEmptyContent'
import NcListItem from '@nextcloud/vue/components/NcListItem'
import NcLoadingIcon from '@nextcloud/vue/components/NcLoadingIcon'
import NcNoteCard from '@nextcloud/vue/components/NcNoteCard'
import NcTextField from '@nextcloud/vue/components/NcTextField'
import AlertCircleIcon from 'vue-material-design-icons/AlertCircle.vue'
import CheckIcon from 'vue-material-design-icons/Check.vue'
import DeleteIcon from 'vue-material-design-icons/Delete.vue'
import ImageIcon from 'vue-material-design-icons/Image.vue'
import ImageOffIcon from 'vue-material-design-icons/ImageOff.vue'
import MagnifyIcon from 'vue-material-design-icons/Magnify.vue'
import PlusIcon from 'vue-material-design-icons/Plus.vue'
import MemeCanvas from '../components/MemeCanvas.vue'
import TextBoxSettings from '../components/TextBoxSettings.vue'
import { getTemplate, hostMeme, searchTemplates, templateImageUrl } from '../api.js'
import { boxForUpload, boxFromTemplate, newBox } from '../boxes.js'
import { FONTS, isFontLoaded } from '../fonts.js'

export default {
	name: 'MemeCustomPickerElement',

	components: {
		AlertCircleIcon,
		CheckIcon,
		DeleteIcon,
		ImageIcon,
		ImageOffIcon,
		MagnifyIcon,
		MemeCanvas,
		NcButton,
		NcEmptyContent,
		NcListItem,
		NcLoadingIcon,
		NcNoteCard,
		NcTextField,
		PlusIcon,
		TextBoxSettings,
	},

	props: {
		providerId: {
			type: String,
			required: true,
		},
		accessible: {
			type: Boolean,
			default: false,
		},
	},

	emits: ['submit'],

	data() {
		return {
			query: '',
			templates: [],
			searching: false,
			searchError: '',
			template: null,
			image: null,
			loadingTemplate: false,
			boxes: [],
			selectedId: null,
			hosting: false,
			hostError: '',
			loadingFonts: [],
			// Fonts whose download failed; a later successful load removes the font again.
			failedFonts: [],
			stageSize: { width: 600, height: 500 },
		}
	},

	computed: {
		hasText() {
			return this.boxes.some((box) => box.text.trim() !== '')
		},

		// Only fonts a box still uses: picking another font for that box also clears the warning.
		fontError() {
			const labels = FONTS
				.filter((font) => this.failedFonts.includes(font.id) && this.boxes.some((box) => box.font === font.id))
				.map((font) => font.label)
			return labels.length
				? t('caption_obvious', 'Could not load {fonts}. The text uses a fallback font.', { fonts: labels.join(', ') })
				: ''
		},
	},

	mounted() {
		this.resizeObserver = new ResizeObserver(([entry]) => {
			this.stageSize = { width: Math.max(200, entry.contentRect.width - 16), height: Math.max(300, entry.contentRect.height - 16) }
		})
		this.resizeObserver.observe(this.$refs.stageArea)
		this.search() // popular templates until the user searches
		setTimeout(() => this.$refs.search?.focus(), 300)
	},

	beforeUnmount() {
		this.resizeObserver?.disconnect()
		clearTimeout(this.searchTimer)
		this.abortController?.abort()
	},

	methods: {
		templateImageUrl,

		onQueryChange() {
			clearTimeout(this.searchTimer)
			this.searchTimer = setTimeout(() => this.search(), 400)
		},

		async search() {
			this.abortController?.abort()
			this.abortController = new AbortController()
			this.searching = true
			this.searchError = ''
			try {
				const results = await searchTemplates(this.query, this.abortController.signal)
				// Still images only: the editor draws on a canvas.
				this.templates = results.filter((item) => item.file_type === 'jpg' || item.file_type === 'png')
			} catch (error) {
				if (error.name !== 'AbortError') {
					this.searchError = t('caption_obvious', 'Search failed: {error}', { error: error.message })
				}
			} finally {
				this.searching = false
			}
		},

		async openTemplate(item) {
			this.loadingTemplate = true
			this.hostError = ''
			try {
				// Popular templates come without boxes; the template endpoint has them.
				const template = item.boxes ? item : await getTemplate(item.id)
				this.image = await loadImage(templateImageUrl(template))
				this.template = template
				this.boxes = template.boxes.map((box) => boxFromTemplate(box, template.width))
				this.selectedId = null
			} catch (error) {
				this.searchError = t('caption_obvious', 'Could not load the template: {error}', { error: error.message })
			} finally {
				this.loadingTemplate = false
			}
			await this.$nextTick()
			if (this.boxes.length > 0) {
				this.$refs[`box-${this.boxes[0].id}`]?.[0]?.focus()
			}
		},

		updateBox(id, changes) {
			const box = this.boxes.find((candidate) => candidate.id === id)
			if (box) {
				Object.assign(box, changes)
			}
		},

		onBoxSettings(id, changes) {
			if (changes.font && !isFontLoaded(changes.font) && !this.loadingFonts.includes(changes.font)) {
				this.loadingFonts.push(changes.font)
			}
			this.updateBox(id, changes)
		},

		retryFailedFonts() {
			for (const font of this.failedFonts) {
				if (this.boxes.some((box) => box.font === font)) {
					this.loadingFonts.push(font)
					this.$refs.canvas?.retryFont(font)
				}
			}
		},

		onFontSettled(font, failed = false) {
			this.loadingFonts = this.loadingFonts.filter((id) => id !== font)
			this.failedFonts = this.failedFonts.filter((id) => id !== font)
			if (failed) {
				this.failedFonts.push(font)
			}
		},

		async addBox() {
			const box = newBox(this.template)
			this.boxes.push(box)
			this.selectedId = box.id
			await this.$nextTick()
			this.$refs[`box-${box.id}`]?.[0]?.focus()
		},

		deleteSelectedBox() {
			this.boxes = this.boxes.filter((box) => box.id !== this.selectedId)
			this.selectedId = null
		},

		async insert() {
			this.hosting = true
			this.hostError = ''
			try {
				const hosted = await hostMeme({
					template_id: this.template.id,
					image: this.$refs.canvas.exportJpeg(),
					texts: this.boxes.map((box) => box.text),
					boxes: this.boxes.map(boxForUpload),
				})
				// The Smart Picker reads the link from a `submit` event on the element it gave us.
				this.$el.dispatchEvent(new CustomEvent('submit', { detail: hosted.url, bubbles: true }))
			} catch (error) {
				this.hostError = t('caption_obvious', 'Could not host the meme: {error}', { error: error.message })
			} finally {
				this.hosting = false
			}
		},
	},
}

/**
 * @param {string} src image URL, same origin
 */
function loadImage(src) {
	return new Promise((resolve, reject) => {
		const image = new Image()
		image.onload = () => resolve(image)
		image.onerror = () => reject(new Error(t('caption_obvious', 'image not available')))
		image.src = src
	})
}
</script>

<style scoped lang="scss">
.caption-obvious-picker {
	flex: 1;
	width: 100%;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	min-height: 560px;
	padding: 12px 16px;

	h2 {
		margin: 0 0 8px;
	}

	.layout {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: 260px minmax(0, 1fr) 320px;
		gap: 16px;

		> * {
			overflow: auto;
			min-height: 0;
		}
	}

	.results {
		margin-top: 8px;
	}

	.thumbnail {
		width: 44px;
		height: 44px;
		object-fit: cover;
		border-radius: var(--border-radius);
	}

	.stage {
		display: flex;
		align-items: flex-start;
		justify-content: center;
	}

	.actions {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-top: 4px;
	}

	.hint {
		color: var(--color-text-maxcontrast);
		text-align: center;
	}
}
</style>
