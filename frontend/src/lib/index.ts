// Point d'entrée central — ré-exporte tous les composants UI
// depuis leur emplacement Atomic Design (spec-004-ui-design-system).
//
// Atoms
export { default as Button } from './ui/atoms/Button.svelte';
export { default as Input } from './ui/atoms/Input.svelte';
export { default as Skeleton } from './ui/atoms/Skeleton.svelte';
export { default as StateBadge } from './ui/atoms/StateBadge.svelte';

// Molecules
export { default as Breadcrumb } from './ui/molecules/Breadcrumb.svelte';
export { default as CompareBar } from './ui/molecules/CompareBar.svelte';
export { default as FiltersPanel } from './ui/molecules/FiltersPanel.svelte';
export { default as QualityBlock } from './ui/molecules/QualityBlock.svelte';
export { default as ResourceList } from './ui/molecules/ResourceList.svelte';
export { default as SkeletonCard } from './ui/molecules/SkeletonCard.svelte';
export { default as StructureBlock } from './ui/molecules/StructureBlock.svelte';

// Organisms
export { default as Card } from './ui/organisms/Card.svelte';
export { default as CardDataset } from './ui/organisms/CardDataset.svelte';
export { default as EmptyState } from './ui/organisms/EmptyState.svelte';

// Icônes SVG néo-brutalistes (PDS-67)
export { default as SearchIcon } from './assets/icons/SearchIcon.svelte';
export { default as FilterIcon } from './assets/icons/FilterIcon.svelte';
export { default as DatasetIcon } from './assets/icons/DatasetIcon.svelte';
export { default as CompareIcon } from './assets/icons/CompareIcon.svelte';
export { default as EmptyIcon } from './assets/icons/EmptyIcon.svelte';
export { default as ErrorIcon } from './assets/icons/ErrorIcon.svelte';
