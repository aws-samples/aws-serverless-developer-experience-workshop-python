.Item | {
    property_id: .property_id.S,
    contract_id: .contract_id.S,
    seller_name: .seller_name.S,
    address: {
        country: .address.M.country.S,
        number:  .address.M.number.N,
        city:    .address.M.city.S,
        street:  .address.M.street.S,
    },
    contract_status: .contract_status.S,
    contract_created: .contract_created.S,
    contract_last_modified_on: .contract_last_modified_on.S
} | del(..|nulls)
