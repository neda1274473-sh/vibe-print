import time
from sentence_transformers import SentenceTransformer

print('Loading model...')
start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2')
load_time = time.time() - start
print(f'Model loaded in {load_time:.2f}s')

start = time.time()
vec = model.encode('test sentence')
enc_time = time.time() - start
print(f'Vector dimension: {len(vec)}')
print(f'Encoding time: {enc_time*1000:.2f} ms')
print(f'First 5 values: {vec[:5]}')
