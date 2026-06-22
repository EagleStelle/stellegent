// Carries the file picked on the lectures list across the client-side nav to
// /lectures/add. A File survives SPA navigation in memory but not a full reload,
// so the add page falls back to its own picker when this is empty.
class PendingUpload {
	file = $state<File | null>(null);

	set(file: File | null) {
		this.file = file;
	}

	clear() {
		this.file = null;
	}
}

export const pendingUpload = new PendingUpload();
