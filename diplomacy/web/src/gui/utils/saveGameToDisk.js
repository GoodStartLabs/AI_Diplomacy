// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================
export function saveGameToDisk(game, onError) {
    if (game.client) {
        game.client.save()
            .then((savedData) => {
                const domLink = document.createElement('a');
                domLink.setAttribute(
                    'href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(JSON.stringify(savedData)));
                domLink.setAttribute('download', `${game.game_id}.json`);
                domLink.style.display = 'none';
                document.body.appendChild(domLink);
                domLink.click();
                document.body.removeChild(domLink);
            })
            .catch(exc => onError(`Error while saving game: ${exc.toString()}`));
    } else {
        onError(`Cannot save this game.`);
    }
}
