// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

contract SimpleStorage {
    uint256 public storedData;

    event DataStored(address indexed sender, uint256 value);

    constructor(uint256 _initialValue) {
        storedData = _initialValue;
        emit DataStored(msg.sender, _initialValue);
    }

    function set(uint256 _value) public {
        storedData = _value;
        emit DataStored(msg.sender, _value);
    }

    function get() public view returns (uint256) {
        return storedData;
    }
}
