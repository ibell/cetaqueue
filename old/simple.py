import os
print('hello from inside simple.py')
with open("/output/oogah.txt",'w') as fp:
   fp.write('hello')
print(os.listdir('/output'))
