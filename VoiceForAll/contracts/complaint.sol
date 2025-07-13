// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ComplaintRegistry {
    struct Complaint {
        string description;
        uint256 votes;
        address submitter;
    }

    Complaint[] public complaints;

    function submitComplaint(string memory _description) public {
        complaints.push(Complaint({
            description: _description,
            votes: 0,
            submitter: msg.sender
        }));
    }

    function voteComplaint(uint _index) public {
        require(_index < complaints.length, "Invalid complaint");
        complaints[_index].votes += 1;
    }

    function getComplaintCount() public view returns (uint) {
        return complaints.length;
    }
}
