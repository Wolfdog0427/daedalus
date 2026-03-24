import { GovernanceConfig } from "daedalus-contract";

export const defaultGovernanceConfig: GovernanceConfig = {
    envelopes: [
        {
            tier: "baseline",
            rules: [],
            constraints: [],
        },
    ],
};
