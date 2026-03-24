export type DaedalusIdentity = {
  nodeId: string;
  label: string;
  deviceType: "mobile";
  platform: "android";
  operator: string;
};

export const IDENTITY: DaedalusIdentity = {
  nodeId: "node-s26-ultra-01",
  label: "S26 Ultra \u00b7 Node 1",
  deviceType: "mobile",
  platform: "android",
  operator: "Wolfdog"
};
