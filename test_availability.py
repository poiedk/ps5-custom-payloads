import json, tempfile, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
import update

class LifecycleTests(unittest.TestCase):
    def test_retire_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old={'id':'gone','name':'Gone','filename':'gone.elf','url':'https://example.org/gone.elf','source_direct':'https://example.org/gone.elf','icon_key':'old'}
            keep={'id':'keep','name':'Keep','icon_key':'keep'}
            sources=[{'id':'gone','repo':'a/gone'},{'id':'keep','repo':'a/keep'}]
            update.write(root/'sources.json',sources)
            update.write(root/'payloads_v2.json',{'payloads':[old,keep]})
            update.write(root/'icons.json',{'icons':{'old':'original','keep':'keep'}})
            def getter(repo):
                if repo=='a/gone':
                    raise urllib.error.HTTPError(repo,404,'missing',{},None)
                return []
            def select(source,releases):
                return dict(old if source['id']=='gone' else keep)
            with patch.object(update,'ROOT',root), patch.object(update,'OUT',root/'payloads_v2.json'), patch.object(update,'select',side_effect=select), patch.object(update,'build_icons',side_effect=lambda a,b,c,d:({'icons':c},{})):
                with patch.object(update,'get',side_effect=getter):
                    update.main()
                archive=json.loads((root/'unavailable.json').read_text())
                self.assertEqual(archive['icons']['old'],'original')
                self.assertNotIn('url',archive['payloads'][0])
                self.assertEqual([x['id'] for x in json.loads((root/'payloads.json').read_text())],['keep'])
                with patch.object(update,'get',return_value=[]):
                    update.main()
                self.assertEqual(json.loads((root/'unavailable.json').read_text())['payloads'],[])
                self.assertEqual(len(json.loads((root/'payloads.json').read_text())),2)

if __name__=='__main__':
    unittest.main()
