export const FACING_OPTIONS = [
  "north", "south", "east", "west", "north_east", "north_west", "south_east", "south_west",
];
export const BUILDING_HEIGHT_OPTIONS = ["low_rise", "high_rise"];
export const HANDOVER_STATUS_OPTIONS = ["ready_to_move", "under_construction"];

export const labelFor = (value) =>
  value ? value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "";