


const jwt = require('jsonwebtoken');
const fs = require('fs');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
var web3_eth_tx = require('./servertest/scripts/notls/web3_eth_tx');

const app = express();
app.use(bodyParser.json());
app.use(cors());

const privateKey = fs.readFileSync('./privateRSAKey.pem');


app.post('/receive', (req, res) => {
    web3_eth_tx.main(req.body);
    res.send('Solicitação POST recebida com sucesso!');
});


app.get('/login', (req, res) => {
    const a = {
    
        "permissions": ["eth:*" ],
        "exp": Math.floor(Date.now() / 1000) + (60 * 60)
    }

    const token = jwt.sign(
        a,
        privateKey,
        { algorithm: 'RS256' }                  // or 'RS256'
    );

    res.send({ token });
});

app.get('/admin', (req, res) => {
    const a = {
    
        "permissions": ["*:*" ],
        "exp": Math.floor(Date.now() / 1000) + (60 * 60)
    }

    const token = jwt.sign(
        a,
        privateKey,
        { algorithm: 'RS256' }                  // or 'RS256'
    );

    res.send({ token });
});


app.get('/', (req, res) => {
    res.send('JWT Server is running');
});

 
app.listen(3000, () => {
    console.log('JWT Server listening on port 3000');
});
