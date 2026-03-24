import { IdentityProfile } from "daedalus-contract";

export class IdentityEngine {
    private profile: IdentityProfile | null = null;

    setProfile(profile: IdentityProfile): void {
        this.profile = profile;
    }

    getProfile(): IdentityProfile | null {
        return this.profile;
    }
}
