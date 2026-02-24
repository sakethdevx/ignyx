from ignyx import Ignyx
app = Ignyx()

@app.get('/plaintext')
def hello():
    return 'Hello World'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
