from apps.personalization.tasks import calculate_rsq_attachment_style as f

def axes(r):
    _, s = f(r)
    mos = (s['secure']+s['dismissive-avoidant']) - (s['fearful-avoidant']+s['anxious-preoccupied'])
    moo = (s['secure']+s['anxious-preoccupied']) - (s['fearful-avoidant']+s['dismissive-avoidant'])
    return mos, moo, max(s, key=s.get)

proto = {
 'SECURE  (+self +other)': {3:5,10:5,15:5,27:5,30:5,9:1,28:1,1:1,5:1,12:1,24:1,2:1,6:1,19:1,22:1,8:3,16:3,25:3},
 'PREOCC  (-self +other)': {8:5,16:5,25:5,9:5,28:5,3:3,10:3,15:3,2:1,6:1,19:1,22:1,1:3,5:3,12:3,24:3},
 'DISMISS (+self -other)': {2:5,6:5,19:5,22:5,3:3,10:2,15:3,9:1,28:1,8:1,16:1,25:1,1:2,5:2,12:2,24:2},
 'FEARFUL (-self -other)': {1:5,5:5,12:5,24:5,9:5,28:5,3:1,10:1,15:1,2:3,6:3,19:3,22:3,8:3,16:3,25:3},
}
print('%-24s %7s %7s   %s' % ('prototype','SELF','OTHER','max()'))
for k, v in proto.items():
    a, b, c = axes({str(x): y for x, y in v.items()})
    print('%-24s %7.2f %7.2f   %s' % (k, a, b, c))
print()
print('all-neutral (blank):', ['%.2f' % x for x in axes({})[:2]])
