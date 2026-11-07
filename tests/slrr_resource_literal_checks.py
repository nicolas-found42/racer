"""Resource qualifiers change lexical syntax, not uint32 identity or slot grammar."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from slrr_vehicle import config,resource_id
class Checks(unittest.TestCase):
 def test_hex_qualified_identity(self):
  for text,value in [('0xE3r',227),('0Xe3R',227),('0xE3',227),('0xFFFFFFFFr',0xffffffff),('0x0r',0),('123',123),('0',0)]:self.assertEqual(resource_id(text),value)
 def test_reject_malformed_negative_overflow_decimal_qualifier(self):
  for text in ('','r','0x','0xr','0x1rr','0x1q','0x1rjunk','-1','-0x1r','+0x1r','0x100000000r','4294967296','123r','01r','0r','1.0',' 0x1r','0x1r ', '0xg1r','cars.parts:0x1r'):
   with self.subTest(token=text),self.assertRaises(ValueError):resource_id(text)
 def test_every_resource_command_and_plain_equivalence(self):
  plain=b'slot 0 0 0 0 0 0 7\nattach 0xE3 8\ncompatible 0xD 9\nstockpart 0xFFFFFFFF\nrender 0xA 1 2 3 0 0 0\ndeformable 0xB\n';qualified=plain.replace(b'0xE3 ',b'0xE3r ').replace(b'0xD ',b'0xDr ').replace(b'0xFFFFFFFF\n',b'0xFFFFFFFFr\n').replace(b'0xA ',b'0xAr ').replace(b'0xB\n',b'0xBr\n');self.assertEqual(config(plain),config(qualified))
 def test_suffix_not_accepted_for_slot_identity(self):
  with self.assertRaises(ValueError):config(b'slot 0 0 0 0 0 0 0x7r\n')
if __name__=='__main__':unittest.main()
