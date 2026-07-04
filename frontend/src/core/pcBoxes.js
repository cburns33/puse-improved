export const VISIBLE_BOX_SEQUENCE = [...Array.from({ length: 24 }, (_, idx) => idx + 1), 26];

export function getBoxLabel(boxId) {
    return Number(boxId) === 26 ? 'Preset' : `Box ${boxId}`;
}
