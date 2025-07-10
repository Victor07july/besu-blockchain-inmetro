
const fs = require('fs');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
var web3_eth_tx = require('../../smart_contracts/scripts/notls/web3_eth_tx');
var web3_eth_txJWT = require('../../smart_contracts/scripts/public/web3_eth_tx');

const app = express();


app.use(bodyParser.json());
app.use(cors());



app.post('/receive', (req, res) => {
    web3_eth_tx.main(req.body);
    res.send('Solicitação POST recebida com sucesso!');
});

app.post('/receivejwt', (req, res) => {
    web3_eth_txJWT.main(req.body);
    res.send('Solicitação POST recebida com sucesso!');
});

app.get('/', (req, res) => {
    res.send('Blockchain Server is running');
});


app.listen(3050, () => {
    console.log('Blockchain Server listening on port 3050');
});
