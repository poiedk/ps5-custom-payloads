# HUMAN_TODO — PayloadForge

## Α. Τι χρειάζεται τώρα
1. Καμία αλλαγή στο PS5 ή στο PLDMGR. Το native installer δεν είναι ακόμη ολοκληρωμένο. Μην ενεργοποιήσεις autoload για PayloadForge.
2. Το SDK v0.42 έχει ήδη μεταγλωττιστεί στο CI· δεν χρειάζεται να μου δώσεις credentials ή να εγκαταστήσεις SDK. Το native ELF είναι μόνο read-only preflight, όχι installer.

## Β. Μόλις υπάρχει πλήρες, CI-verified native RC
3. Έλεγξε Settings → System → System Software → Console Information: firmware 13.60. Κατάγραψε επίσης μοντέλο PS5 και έκδοση PLDMGR. Μην κάνεις αναβάθμιση firmware.
4. Από το συγκεκριμένο GitHub Actions run κατέβασε το υποψήφιο native artifact και το SHA256SUMS. Επαλήθευσε το SHA-256 πριν από οποιαδήποτε εκτέλεση. Αν δεν υπάρχει πλήρες native RC ή δεν ταιριάζει το hash, μην προχωρήσεις. Το payloadforge-preflight.elf δεν θεωρείται πλήρες RC.
5. Κράτησε backup των σχετικών app-owned configs και PLDMGR ρυθμίσεων, επιβεβαίωσε ελεύθερο χώρο και χρησιμοποίησε αποκλειστικά δοκιμαστικά data-only bundles. Καμία αλλαγή σε Y2JB, WebKit, boot chain ή πραγματική βιβλιοθήκη.

## Γ. Hardware test plan (Stage 15)
6. Install demo v1: επιβεβαίωσε version, registry και hashes των δοκιμαστικών αρχείων.
7. Μέσω του εγκεκριμένου native test harness άλλαξε μόνο το demo settings.json. Κάνε update v2: το δικό σου setting πρέπει να μείνει, ενώ το demo asset πρέπει να ενημερωθεί. Αν δεν υπάρχει ασφαλής τρόπος αλλαγής του demo config, σημείωσε BLOCKED.
8. Κάνε manual backup, rollback στη v1 και έλεγξε ότι μένει το τελευταίο config. Δοκίμασε λανθασμένο checksum, αλλοιωμένο snapshot, missing dependency και resource conflict: όλα πρέπει να μπλοκάρουν χωρίς αλλαγή ενεργής έκδοσης.
9. Δοκίμασε uninstall με και χωρίς διατήρηση config, ύστερα reinstall. Τα μη καταχωρισμένα αρχεία δεν πρέπει να διαγραφούν. Τα backups παραμένουν διαθέσιμα.
10. Έλεγξε μέσω ειδικού test hook προσομοιωμένη διακοπή πριν/μετά την ενεργοποίηση. Μην αφαιρέσεις σκόπιμα την τροφοδοσία του PS5. Επιβεβαίωσε ότι υπάρχει έγκυρη ενεργή έκδοση ή εμφανής αναφορά ανάκτησης.
11. Έλεγξε ότι ο PLDMGR διατηρεί ακριβώς το source URL, τα υπάρχοντα IDs, τα favorites και τις ρυθμίσεις. Μην αλλάξεις autoload.
12. Στείλε αποτελέσματα ανά test: PASS/FAIL/BLOCKED, έκδοση RC, firmware, σχετικά logs και παρατηρήσεις. Μην στείλεις credentials ή προσωπικά δεδομένα.

## Δ. Τελική έγκριση (Stage 16)
13. Πριν από διανομή, ελέγχουμε προέλευση/άδειες/αντίστοιχο πηγαίο κώδικα του native build και κάθε νέου package. Οι αμφίβολες πηγές μένουν στο review-candidates.json.
14. Stable release και προώθηση στο main μόνο μετά από πλήρη native engine, πράσινο CI και πραγματικά επιτυχημένα hardware tests. Δεν έχει εκδοθεί stable release.
