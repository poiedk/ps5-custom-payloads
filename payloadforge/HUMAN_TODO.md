# HUMAN_TODO — PayloadForge v0.2.0-rc0-demo

## Α. Πριν από οποιαδήποτε δοκιμή
1. Καμία αλλαγή σε Y2JB, WebKit, boot chain, autoload, πραγματική βιβλιοθήκη ή ρυθμίσεις PLDMGR. Δεν απαιτείται προσωπικό credential. Δεν υπάρχει stable release.
2. Χρησιμοποίησε μόνο το CI artifact `payloadforge-0.2.0-rc0-demo-hardware-kit` εφόσον το συγκεκριμένο GitHub Actions run έχει ολοκληρωθεί επιτυχώς. Αν δεν υπάρχει, μην προχωρήσεις. Έλεγξε CANDIDATE.json, SHA256SUMS και τα hashes του ELF/fixtures.
3. Κατάγραψε μοντέλο, πραγματικό firmware 13.60 και έκδοση PLDMGR χωρίς firmware update. Κράτησε backup των σχετικών ρυθμίσεων.
4. Επιβεβαίωσε ότι ο υπάρχων εξουσιοδοτημένος τοπικός launcher επιτρέπει ρητά argv και ασφαλή ανάγνωση stdout. Η απαίτηση για το managed demo είναι `--serve-managed --root /data/payloadforge-demo --port 0 --seconds 300`. Το root πρέπει να είναι ήδη υπάρχον, ιδιωτικό, χωρίς symlinks. Δεν παρέχεται ούτε απαιτείται νέος loader. Αν το υπάρχον περιβάλλον δεν υποστηρίζει αυτά τα prerequisites, σημείωσε BLOCKED· μην αλλάξεις boot chain ή δίκτυο για να το παρακάμψεις.
5. Η πρόσβαση γίνεται μόνο από browser στην ίδια κονσόλα, στη διεύθυνση loopback που αναφέρει ο launcher. Ο προσωρινός session token δεν πρέπει να κοινοποιηθεί. Αν ο τοπικός browser/file picker δεν είναι διαθέσιμος, σημείωσε BLOCKED, όχι PASS.

## Β. Δοκιμές
6. Εκτέλεσε το HARDWARE_TEST_MATRIX.md από H01 έως H13. Χρησιμοποίησε αποκλειστικά τα μικρά συνθετικά data-only fixtures του kit.
7. Για αλλαγή demo config, χρησιμοποιήσε μόνο ήδη εξουσιοδοτημένο τοπικό εργαλείο και μόνο το demo settings.json. Αν δεν υπάρχει ασφαλής τρόπος, BLOCKED. Μην πειράξεις αρχεία άλλων apps.
8. Δεν υπάρχει παραγωγικό fault-injection hook. Μην προκαλέσεις διακοπή τροφοδοσίας. Αν δεν υπάρχει εγκεκριμένος τρόπος προσομοίωσης διακοπής, σημείωσε το αντίστοιχο test BLOCKED.
9. Σε αβέβαιη απάντηση συναλλαγής, έλεγξε πρώτα status/recovery· μην επαναλάβεις αυτόματα την ενέργεια.
10. Συμπλήρωσε HARDWARE_RESULT_TEMPLATE.json με PASS/FAIL/BLOCKED, πραγματική έκδοση και αποδεικτικά. Μην στείλεις tokens, credentials ή προσωπικά δεδομένα.

## Γ. Τελική έγκριση
11. Το demo candidate ΔΕΝ εγκαθιστά κανονικά ELF payloads και δεν ενσωματώνεται ως αυτόματος loader. Ο κατάλογος PLDMGR είναι read-only reference. Εγκεκριμένα companion πακέτα: 0.
12. Full installer και stable release παραμένουν μπλοκαρισμένα έως πραγματικά επιτυχημένα hardware tests, επαληθευμένη συμβατότητα launcher/browser, τεκμηριωμένη προέλευση πακέτων και ξεχωριστή έγκριση παραγωγής.
